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

export async function fetchCampusBuildings(bbox, fallbackLayers = {}) {
  if (!bbox) {
    return {
      type: 'FeatureCollection',
      features: []
    }
  }

  const expanded = {
    west: bbox.west - 0.0008,
    east: bbox.east + 0.0008,
    south: bbox.south - 0.0008,
    north: bbox.north + 0.0008
  }

  const overpassQuery = `
    [out:json][timeout:30];
    (
      way["building"](${expanded.south},${expanded.west},${expanded.north},${expanded.east});
      relation["building"](${expanded.south},${expanded.west},${expanded.north},${expanded.east});
    );
    out body;
    >;
    out skel qt;
  `.trim()

  try {
    const response = await fetch('https://overpass-api.de/api/interpreter', {
      method: 'POST',
      headers: {
        'Content-Type': 'text/plain;charset=UTF-8'
      },
      body: overpassQuery
    })

    if (!response.ok) {
      throw new Error('building fetch failed')
    }

    const data = await response.json()
    const geojson = overpassToGeojson(data)

    if (geojson.features.length) {
      return geojson
    }
  } catch {
    // Ignore remote fetch failures and fall back to locally derived campus blocks.
  }

  return buildFallbackBuildings(bbox, fallbackLayers)
}

function overpassToGeojson(data) {
  const elements = data?.elements ?? []
  const nodes = new Map()
  const ways = new Map()

  for (const element of elements) {
    if (element.type === 'node') {
      nodes.set(element.id, [element.lon, element.lat])
    } else if (element.type === 'way') {
      ways.set(element.id, element)
    }
  }

  const wayFeatures = elements
    .filter((element) => element.type === 'way' && element.tags?.building && element.nodes?.length >= 3)
    .map((element) => buildWayFeature(element, nodes))
    .filter(Boolean)

  const relationFeatures = elements
    .filter((element) => element.type === 'relation' && element.tags?.building && element.members?.length)
    .map((element) => buildRelationFeature(element, ways, nodes))
    .filter(Boolean)

  const deduped = dedupeFeatures([...wayFeatures, ...relationFeatures])

  return {
    type: 'FeatureCollection',
    features: deduped
  }
}

function buildWayFeature(element, nodes) {
  const ring = buildRingFromNodeIds(element.nodes, nodes)
  if (!ring) {
    return null
  }

  return createBuildingFeature(ring, element.tags)
}

function buildRelationFeature(element, ways, nodes) {
  const outerRings = element.members
    .filter((member) => member.type === 'way' && member.role === 'outer')
    .map((member) => ways.get(member.ref))
    .filter(Boolean)
    .map((way) => buildRingFromNodeIds(way.nodes, nodes))
    .filter(Boolean)

  if (!outerRings.length) {
    return null
  }

  const longestOuter = outerRings.sort((a, b) => polygonArea(b) - polygonArea(a))[0]
  return createBuildingFeature(longestOuter, element.tags)
}

function buildRingFromNodeIds(nodeIds, nodes) {
  const coordinates = nodeIds
    .map((nodeId) => nodes.get(nodeId))
    .filter(Boolean)

  if (coordinates.length < 3) {
    return null
  }

  const first = coordinates[0]
  const last = coordinates[coordinates.length - 1]

  return first[0] === last[0] && first[1] === last[1]
    ? coordinates
    : [...coordinates, first]
}

function createBuildingFeature(ring, tags = {}) {
  return {
    type: 'Feature',
    geometry: {
      type: 'Polygon',
      coordinates: [ring]
    },
    properties: {
      name: tags.name ?? '校园建筑',
      building: tags.building ?? 'yes',
      levels: Number(tags['building:levels'] ?? 0),
      height:
        Number.parseFloat(tags.height ?? '') ||
        Number(tags['building:levels'] ?? 0) * 3.6 ||
        18
    }
  }
}

function polygonArea(ring) {
  let area = 0
  for (let i = 0; i < ring.length - 1; i += 1) {
    const [x1, y1] = ring[i]
    const [x2, y2] = ring[i + 1]
    area += x1 * y2 - x2 * y1
  }
  return Math.abs(area / 2)
}

function dedupeFeatures(features) {
  const seen = new Set()
  const result = []

  for (const feature of features) {
    const ring = feature.geometry?.coordinates?.[0]
    if (!ring?.length) {
      continue
    }

    const key = ring
      .slice(0, -1)
      .map(([lng, lat]) => `${lng.toFixed(6)},${lat.toFixed(6)}`)
      .join('|')

    if (seen.has(key)) {
      continue
    }

    seen.add(key)
    result.push(feature)
  }

  return result
}

function buildFallbackBuildings(bbox, fallbackLayers = {}) {
  const points = collectFallbackPoints(fallbackLayers)

  if (!points.length) {
    return {
      type: 'FeatureCollection',
      features: [createBoxBuildingFromCenter(getBboxCenter(bbox), bbox, 0, '校园建筑')]
    }
  }

  return {
    type: 'FeatureCollection',
    features: points.map((point, index) =>
      createBoxBuildingFromCenter(point.coordinates, bbox, index, point.name)
    )
  }
}

function collectFallbackPoints(fallbackLayers) {
  const collections = [
    fallbackLayers.facilities,
    fallbackLayers.assembly,
    fallbackLayers.hazards
  ]
  const points = []
  const seen = new Set()

  collections.forEach((collection) => {
    const features = collection?.features ?? []
    features.forEach((feature) => {
      if (feature?.geometry?.type !== 'Point' || !Array.isArray(feature.geometry.coordinates)) {
        return
      }

      const [lng, lat] = feature.geometry.coordinates
      const key = `${lng.toFixed(5)},${lat.toFixed(5)}`

      if (seen.has(key)) {
        return
      }

      seen.add(key)
      points.push({
        coordinates: [lng, lat],
        name:
          feature.properties?.name ||
          feature.properties?.facility_name ||
          feature.properties?.title ||
          '校园建筑'
      })
    })
  })

  return points.slice(0, 18)
}

function createBoxBuildingFromCenter(center, bbox, index, name) {
  const [lng, lat] = center
  const width = Math.max((bbox.east - bbox.west) * 0.018, 0.00005)
  const height = Math.max((bbox.north - bbox.south) * 0.014, 0.00004)
  const offsetLng = ((index % 3) - 1) * width * 0.55
  const offsetLat = (Math.floor(index / 3) % 3 - 1) * height * 0.55
  const cx = lng + offsetLng
  const cy = lat + offsetLat

  return {
    type: 'Feature',
    geometry: {
      type: 'Polygon',
      coordinates: [[
        [cx - width, cy - height],
        [cx + width, cy - height],
        [cx + width, cy + height],
        [cx - width, cy + height],
        [cx - width, cy - height]
      ]]
    },
    properties: {
      name,
      building: 'fallback',
      levels: 4 + (index % 5),
      height: 16 + (index % 6) * 4
    }
  }
}

function getBboxCenter(bbox) {
  return [
    (bbox.west + bbox.east) / 2,
    (bbox.south + bbox.north) / 2
  ]
}
