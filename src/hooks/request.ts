import { useLoading } from 'hooks/loading'
import { folderCache } from 'hooks/folderCache'
import { api } from 'scripts/comfyAPI'
import { onMounted, ref } from 'vue'

/**
 * Get cached data instantly (synchronous, no network)
 * Returns null if not in cache
 */
export const getCachedData = <T>(url: string): T | null => {
  return folderCache.getData<T>(url)
}

/**
 * Check if data is cached
 */
export const isCached = (url: string): boolean => {
  return folderCache.has(url)
}

/**
 * Low-level fetch with ETag/conditional request support
 */
export const requestWithCache = async (url: string, options?: RequestInit & { skipCache?: boolean }) => {
  const cacheKey = url
  const cachedEtag = options?.skipCache ? null : folderCache.getEtag(cacheKey)
  
  const headers: Record<string, string> = {
    ...(options?.headers as Record<string, string> || {}),
  }
  
  // Add conditional request header if we have cached data
  if (cachedEtag) {
    headers['If-None-Match'] = cachedEtag
  }

  const response = await api.fetchApi(`/image-browsing${url}`, {
    ...options,
    headers,
  })

  // Handle 304 Not Modified - return cached data
  if (response.status === 304) {
    const cached = folderCache.get(cacheKey)
    if (cached) {
      return { data: cached.data, fromCache: true }
    }
    // Cache miss after 304 - shouldn't happen, but fallback to fresh request
    return requestWithCache(url, { ...options, skipCache: true })
  }

  const resData = await response.json()
  
  if (resData.success) {
    // Store in cache with ETag
    const etag = response.headers.get('ETag') || response.headers.get('X-Folder-Hash') || ''
    if (etag) {
      folderCache.set(cacheKey, resData.data, etag)
    }
    return { data: resData.data, fromCache: false }
  }
  
  throw new Error(resData.error)
}

/**
 * Simple request without caching (for mutations)
 */
export const request = async (url: string, options?: RequestInit) => {
  // For GET requests to folder paths, use cache
  const method = options?.method?.toUpperCase() || 'GET'
  const isFolderGet = method === 'GET' && (
    url.startsWith('/output') || 
    url.startsWith('/workflows') || 
    url.startsWith('/prompts')
  ) && !url.includes('?')
  
  if (isFolderGet) {
    const result = await requestWithCache(url, options)
    return result.data
  }

  // Non-cached request
  return api
    .fetchApi(`/image-browsing${url}`, options)
    .then((response) => response.json())
    .then((resData) => {
      if (resData.success) {
        return resData.data
      }
      throw new Error(resData.error)
    })
}

/**
 * Invalidate cache for a path (call after mutations)
 */
export const invalidateCache = (path: string) => {
  folderCache.invalidate(path)
}

/**
 * Invalidate cache for path and all children
 */
export const invalidateCachePrefix = (pathPrefix: string) => {
  folderCache.invalidatePrefix(pathPrefix)
}

/**
 * Prefetch folder data in background
 */
export const prefetchFolder = async (path: string) => {
  // Don't prefetch if already cached
  if (folderCache.has(path)) return
  
  try {
    await requestWithCache(path)
  } catch {
    // Ignore prefetch errors
  }
}

/**
 * Prefetch multiple folders in parallel
 */
export const prefetchFolders = async (paths: string[]) => {
  const uncached = paths.filter(p => !folderCache.has(p))
  if (uncached.length === 0) return
  
  await Promise.allSettled(uncached.map(p => requestWithCache(p)))
}

/**
 * Revalidate cache in background (stale-while-revalidate pattern)
 * Returns immediately with cached data, then updates cache in background
 */
export const revalidateInBackground = (path: string): void => {
  // Fire and forget - update cache in background
  requestWithCache(path).catch(() => {
    // Ignore revalidation errors
  })
}

export interface RequestOptions<T> {
  method?: RequestInit['method']
  headers?: RequestInit['headers']
  defaultParams?: Record<string, any>
  defaultValue?: any
  postData?: (data: T) => T
  manual?: boolean
}

export const useRequest = <T = any>(
  url: string,
  options: RequestOptions<T> = {},
) => {
  const loading = useLoading()
  const postData = options.postData ?? ((data) => data)

  const data = ref<T>(options.defaultValue)
  const lastParams = ref()

  const fetch = async (
    params: Record<string, any> = options.defaultParams ?? {},
  ) => {
    loading.show()

    lastParams.value = params

    let requestUrl = url
    const requestOptions: RequestInit = {
      method: options.method,
      headers: options.headers,
    }
    const requestParams = { ...params }

    const templatePattern = /\{(.*?)\}/g
    const urlParamKeyMatches = requestUrl.matchAll(templatePattern)
    for (const urlParamKey of urlParamKeyMatches) {
      const [match, paramKey] = urlParamKey
      if (paramKey in requestParams) {
        const paramValue = requestParams[paramKey]
        delete requestParams[paramKey]
        requestUrl = requestUrl.replace(match, paramValue)
      }
    }

    if (!requestOptions.method) {
      requestOptions.method = 'GET'
    }

    if (requestOptions.method !== 'GET') {
      requestOptions.body = JSON.stringify(requestParams)
    }

    return request(requestUrl, requestOptions)
      .then((resData) => (data.value = postData(resData)))
      .finally(() => loading.hide())
  }

  onMounted(() => {
    if (!options.manual) {
      fetch()
    }
  })

  const refresh = async () => {
    return fetch(lastParams.value)
  }

  return { data, refresh, fetch }
}
