const API_BASE = '/api'

async function parseJson(response) {
  const text = await response.text()

  if (!text) {
    return null
  }

  try {
    return JSON.parse(text)
  } catch {
    throw new Error('后端返回了无法解析的数据')
  }
}

export async function submitSmartQuery(payload) {
  const response = await fetch(`${API_BASE}/query`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  })

  const data = await parseJson(response)

  if (!response.ok) {
    throw new Error(data?.detail || '后端请求失败')
  }

  return data
}

export async function fetchHealth() {
  const response = await fetch(`${API_BASE}/health`)
  const data = await parseJson(response)

  if (!response.ok) {
    throw new Error(data?.detail || '健康检查失败')
  }

  return data
}

export async function fetchMapLayer(layerName) {
  const response = await fetch(`${API_BASE}/map/${layerName}`)
  const data = await parseJson(response)

  if (!response.ok) {
    throw new Error(data?.detail || '地图图层请求失败')
  }

  return data
}
