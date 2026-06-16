<template>
  <section class="panel map-panel">
    <div class="map-panel-top">
      <div>
        <p class="eyebrow">Immersive Safety Map</p>
        <h2>校园空间态势图</h2>
      </div>
      <div class="toolbar-actions">
        <button
          class="mini-button"
          :class="{ active: viewMode === '2d' }"
          @click="setViewMode('2d')"
        >
          2D 总览
        </button>
        <button
          class="mini-button"
          :class="{ active: viewMode === '3d' }"
          @click="setViewMode('3d')"
        >
          3D 沉浸
        </button>
        <button class="mini-button" @click="focusOnRoute">聚焦路线</button>
      </div>
    </div>

    <div class="live-stat-strip">
      <article
        v-for="item in stats"
        :key="item.label"
        class="live-stat-card"
        :class="`tone-${item.tone}`"
      >
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
      </article>
    </div>

    <div class="map-stage cinematic-map-shell">
      <div ref="mapRoot" class="maplibre-host"></div>

      <div class="map-top-strip">
        <div class="map-top-card">
          <span class="map-overlay-badge">{{ viewMode === '3d' ? '3D Camera' : '2D Camera' }}</span>
          <strong>{{ summary.mode }}</strong>
          <p>{{ summary.message }}</p>
        </div>

        <div class="map-legend-card">
          <span class="legend-title">图层图例</span>
          <div class="legend-list">
            <span class="legend-chip legend-route">推荐路线</span>
            <span class="legend-chip legend-road">道路网</span>
            <span class="legend-chip legend-hazard">风险点</span>
            <span class="legend-chip legend-assembly">疏散点</span>
          </div>
        </div>
      </div>

      <div class="map-overlay-copy">
        <div class="map-overlay-badge">OpenStreetMap + MapLibre</div>
        <p>{{ overlayMessage }}</p>
      </div>

      <div class="route-summary-card editorial-card">
        <span class="route-tag">{{ summary.dataSource }}</span>
        <strong>{{ summary.title }}</strong>
        <p>{{ summary.mode }}</p>
        <div class="route-metrics">
          <span>{{ summary.distance }}</span>
          <span>{{ summary.eta }}</span>
          <span>{{ summary.score }}</span>
        </div>
      </div>
    </div>

    <div class="timeline-card">
      <div class="section-head">
        <h2>路径时间线</h2>
        <span class="muted-mini">Route Timeline</span>
      </div>
      <div class="timeline-list">
        <article
          v-for="item in timeline"
          :key="`${item.time}-${item.title}`"
          class="timeline-item"
          :class="`state-${item.state}`"
        >
          <span class="timeline-time">{{ item.time }}</span>
          <div class="timeline-body">
            <strong>{{ item.title }}</strong>
            <p>{{ item.detail }}</p>
          </div>
        </article>
      </div>
    </div>
  </section>
</template>

<script setup>
import maplibregl from 'maplibre-gl'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  summary: {
    type: Object,
    required: true
  },
  stats: {
    type: Array,
    required: true
  },
  timeline: {
    type: Array,
    required: true
  },
  layers: {
    type: Array,
    required: true
  },
  routeGeojson: {
    type: Object,
    default: null
  },
  facilities: {
    type: Array,
    default: () => []
  },
  mapLayers: {
    type: Object,
    default: () => ({
      roads: null,
      hazards: null,
      assembly: null,
      facilities: null
    })
  }
})

const mapRoot = ref(null)
const viewMode = ref('2d')
const defaultCenter = [114.613, 30.458]

const roadLayerIds = ['roads-casing', 'roads-line', 'roads-lighting']
const hazardLayerIds = ['hazards-pulse', 'hazards-points']
const assemblyLayerIds = ['assembly-pulse', 'assembly-points']
const facilityLayerIds = ['facilities-points']
const routeLayerIds = ['route-glow', 'route-core']

let mapInstance = null
let mapLoaded = false
let hasFitInitialData = false

const activeLayers = computed(() =>
  props.layers.reduce((acc, layer) => {
    acc[layer.id] = layer.active
    return acc
  }, {})
)

const overlayMessage = computed(() => {
  if (viewMode.value === '3d') {
    return '三维视角会倾斜镜头并抬升建筑，让道路网、风险点和疏散点更容易分层辨认。'
  }

  return '二维视角适合总览全局，图层会保持清晰配色，便于查看路线、路网和风险分布。'
})

function buildMapStyle() {
  return {
    version: 8,
    glyphs: 'https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf',
    sources: {
      osm: {
        type: 'raster',
        tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
        tileSize: 256,
        attribution: '&copy; OpenStreetMap contributors'
      }
    },
    layers: [
      {
        id: 'osm-base',
        type: 'raster',
        source: 'osm',
        paint: {
          'raster-opacity': 1,
          'raster-saturation': -0.1,
          'raster-contrast': 0.15,
          'raster-brightness-min': 0.08,
          'raster-brightness-max': 0.96
        }
      }
    ]
  }
}

function ensureSource(sourceId, data) {
  if (!mapInstance || !mapLoaded) {
    return
  }

  const source = mapInstance.getSource(sourceId)
  if (source) {
    source.setData(data)
    return
  }

  mapInstance.addSource(sourceId, {
    type: 'geojson',
    data
  })
}

function ensureLayer(layer, beforeId) {
  if (!mapInstance || !mapLoaded || mapInstance.getLayer(layer.id)) {
    return
  }

  mapInstance.addLayer(layer, beforeId)
}

function setLayerVisibility(layerIds, visible) {
  if (!mapInstance || !mapLoaded) {
    return
  }

  for (const layerId of layerIds) {
    if (mapInstance.getLayer(layerId)) {
      mapInstance.setLayoutProperty(layerId, 'visibility', visible ? 'visible' : 'none')
    }
  }
}

function toFeatureCollection(features) {
  return {
    type: 'FeatureCollection',
    features
  }
}

function normalizeFacilities() {
  const derivedFeatures = props.facilities
    .filter((item) => item.coordinate?.lng && item.coordinate?.lat)
    .map((item) => ({
      type: 'Feature',
      geometry: {
        type: 'Point',
        coordinates: [item.coordinate.lng, item.coordinate.lat]
      },
      properties: {
        name: item.facility_name ?? '服务设施',
        category: item.facility_type ?? '未分类设施',
        night_available: Boolean(item.night_available),
        is_evacuation_point: Boolean(item.is_evacuation_point),
        remark: item.remark ?? ''
      }
    }))

  if (props.mapLayers.facilities?.features?.length) {
    return props.mapLayers.facilities
  }

  return toFeatureCollection(derivedFeatures)
}

function getBoundsFromGeojson(geojson) {
  const bounds = new maplibregl.LngLatBounds()
  let hasCoordinate = false

  function extendCoordinates(coordinates) {
    if (!Array.isArray(coordinates)) {
      return
    }

    if (typeof coordinates[0] === 'number' && typeof coordinates[1] === 'number') {
      bounds.extend([coordinates[0], coordinates[1]])
      hasCoordinate = true
      return
    }

    for (const item of coordinates) {
      extendCoordinates(item)
    }
  }

  if (geojson?.type === 'FeatureCollection') {
    geojson.features.forEach((feature) => extendCoordinates(feature.geometry?.coordinates))
  } else if (geojson?.type === 'Feature') {
    extendCoordinates(geojson.geometry?.coordinates)
  } else if (geojson?.coordinates) {
    extendCoordinates(geojson.coordinates)
  }

  return hasCoordinate ? bounds : null
}

function fitToBestBounds() {
  if (!mapInstance || !mapLoaded) {
    return
  }

  const routeBounds = getBoundsFromGeojson(props.routeGeojson)
  if (routeBounds) {
    mapInstance.fitBounds(routeBounds, {
      padding: 72,
      duration: 900,
      pitch: viewMode.value === '3d' ? 58 : 0,
      bearing: viewMode.value === '3d' ? -22 : 0
    })
    return
  }

  const roadBounds = getBoundsFromGeojson(props.mapLayers.roads)
  if (roadBounds && !hasFitInitialData) {
    mapInstance.fitBounds(roadBounds, {
      padding: 72,
      duration: 0
    })
    hasFitInitialData = true
    return
  }

  if (!hasFitInitialData) {
    mapInstance.jumpTo({
      center: defaultCenter,
      zoom: 16,
      pitch: 0,
      bearing: 0
    })
    hasFitInitialData = true
  }
}

function ensureMapLayers() {
  const emptyCollection = toFeatureCollection([])
  const facilitiesGeojson = normalizeFacilities()

  ensureSource('campus-roads', props.mapLayers.roads ?? emptyCollection)
  ensureSource('campus-hazards', props.mapLayers.hazards ?? emptyCollection)
  ensureSource('campus-assembly', props.mapLayers.assembly ?? emptyCollection)
  ensureSource('campus-facilities', facilitiesGeojson ?? emptyCollection)
  ensureSource('campus-route', props.routeGeojson ?? emptyCollection)

  ensureLayer({
    id: 'roads-casing',
    type: 'line',
    source: 'campus-roads',
    layout: {
      'line-cap': 'round',
      'line-join': 'round'
    },
    paint: {
      'line-color': '#173a52',
      'line-width': [
        'interpolate',
        ['linear'],
        ['zoom'],
        14,
        4,
        18,
        12
      ],
      'line-opacity': 0.35
    }
  })

  ensureLayer({
    id: 'roads-line',
    type: 'line',
    source: 'campus-roads',
    layout: {
      'line-cap': 'round',
      'line-join': 'round'
    },
    paint: {
      'line-color': [
        'case',
        ['<', ['coalesce', ['to-number', ['get', 'lighting_score']], 8], 5],
        '#f3a847',
        '#74a4ff'
      ],
      'line-width': [
        'interpolate',
        ['linear'],
        ['zoom'],
        14,
        2.2,
        18,
        5.2
      ],
      'line-opacity': 0.88
    }
  })

  ensureLayer({
    id: 'roads-lighting',
    type: 'line',
    source: 'campus-roads',
    layout: {
      'line-cap': 'round',
      'line-join': 'round'
    },
    paint: {
      'line-color': [
        'case',
        ['<', ['coalesce', ['to-number', ['get', 'lighting_score']], 8], 5],
        '#ffd08a',
        '#d7f0ff'
      ],
      'line-width': [
        'interpolate',
        ['linear'],
        ['zoom'],
        14,
        0.8,
        18,
        2
      ],
      'line-opacity': 0.72,
      'line-blur': 0.4
    }
  })

  ensureLayer({
    id: 'route-glow',
    type: 'line',
    source: 'campus-route',
    layout: {
      'line-cap': 'round',
      'line-join': 'round'
    },
    paint: {
      'line-color': '#d8fff5',
      'line-width': [
        'interpolate',
        ['linear'],
        ['zoom'],
        14,
        8,
        18,
        18
      ],
      'line-opacity': 0.5,
      'line-blur': 1.4
    }
  })

  ensureLayer({
    id: 'route-core',
    type: 'line',
    source: 'campus-route',
    layout: {
      'line-cap': 'round',
      'line-join': 'round'
    },
    paint: {
      'line-color': '#0e8f73',
      'line-width': [
        'interpolate',
        ['linear'],
        ['zoom'],
        14,
        4,
        18,
        8
      ],
      'line-opacity': 0.98
    }
  })

  ensureLayer({
    id: 'hazards-pulse',
    type: 'circle',
    source: 'campus-hazards',
    paint: {
      'circle-radius': [
        'interpolate',
        ['linear'],
        ['zoom'],
        14,
        9,
        18,
        16
      ],
      'circle-color': '#ffb0a2',
      'circle-opacity': 0.28,
      'circle-blur': 0.6
    }
  })

  ensureLayer({
    id: 'hazards-points',
    type: 'circle',
    source: 'campus-hazards',
    paint: {
      'circle-radius': [
        'interpolate',
        ['linear'],
        ['zoom'],
        14,
        4,
        18,
        8
      ],
      'circle-color': '#d35d4e',
      'circle-stroke-color': '#fffaf6',
      'circle-stroke-width': 2,
      'circle-opacity': 0.96
    }
  })

  ensureLayer({
    id: 'assembly-pulse',
    type: 'circle',
    source: 'campus-assembly',
    paint: {
      'circle-radius': [
        'interpolate',
        ['linear'],
        ['zoom'],
        14,
        10,
        18,
        18
      ],
      'circle-color': '#b7ffdf',
      'circle-opacity': 0.22,
      'circle-blur': 0.6
    }
  })

  ensureLayer({
    id: 'assembly-points',
    type: 'circle',
    source: 'campus-assembly',
    paint: {
      'circle-radius': [
        'interpolate',
        ['linear'],
        ['zoom'],
        14,
        5,
        18,
        9
      ],
      'circle-color': '#159b76',
      'circle-stroke-color': '#ffffff',
      'circle-stroke-width': 2,
      'circle-opacity': 0.96
    }
  })

  ensureLayer({
    id: 'facilities-points',
    type: 'circle',
    source: 'campus-facilities',
    paint: {
      'circle-radius': [
        'interpolate',
        ['linear'],
        ['zoom'],
        14,
        4,
        18,
        8
      ],
      'circle-color': [
        'case',
        ['boolean', ['get', 'is_evacuation_point'], false],
        '#0caa74',
        ['boolean', ['get', 'night_available'], false],
        '#e3ab42',
        '#5679dc'
      ],
      'circle-stroke-color': '#ffffff',
      'circle-stroke-width': 2,
      'circle-opacity': 0.95
    }
  })
}

function updateLayerVisibility() {
  setLayerVisibility(roadLayerIds, activeLayers.value.roads)
  setLayerVisibility(hazardLayerIds, activeLayers.value.hazards)
  setLayerVisibility(assemblyLayerIds, activeLayers.value.assembly)
  setLayerVisibility(facilityLayerIds, activeLayers.value.facilities)
  setLayerVisibility(routeLayerIds, Boolean(props.routeGeojson?.geometry?.coordinates?.length))
}

function buildExtrusionsFromRoads() {
  const roadFeatures = props.mapLayers.roads?.features ?? []
  const extrusions = roadFeatures
    .map((feature, index) => {
      const coordinates = feature.geometry?.coordinates
      if (!Array.isArray(coordinates) || coordinates.length < 2) {
        return null
      }

      const line = feature.geometry.type === 'LineString' ? coordinates : coordinates[0]
      if (!Array.isArray(line) || line.length < 2) {
        return null
      }

      const [start, end] = line
      const width = 0.00006
      const dx = end[0] - start[0]
      const dy = end[1] - start[1]
      const length = Math.hypot(dx, dy) || 1
      const offsetX = (-dy / length) * width
      const offsetY = (dx / length) * width

      return {
        type: 'Feature',
        id: `road-extrusion-${index}`,
        geometry: {
          type: 'Polygon',
          coordinates: [[
            [start[0] + offsetX, start[1] + offsetY],
            [end[0] + offsetX, end[1] + offsetY],
            [end[0] - offsetX, end[1] - offsetY],
            [start[0] - offsetX, start[1] - offsetY],
            [start[0] + offsetX, start[1] + offsetY]
          ]]
        },
        properties: {
          height: 8 + (feature.properties?.lighting_score ?? 8),
          color: Number(feature.properties?.lighting_score ?? 8) < 5 ? '#ad6a2a' : '#3f6db2'
        }
      }
    })
    .filter(Boolean)

  return toFeatureCollection(extrusions)
}

function ensureExtrusionLayer() {
  ensureSource('campus-road-extrusions', buildExtrusionsFromRoads())

  ensureLayer({
    id: 'road-extrusions',
    type: 'fill-extrusion',
    source: 'campus-road-extrusions',
    paint: {
      'fill-extrusion-color': ['coalesce', ['get', 'color'], '#3f6db2'],
      'fill-extrusion-height': ['coalesce', ['to-number', ['get', 'height']], 12],
      'fill-extrusion-base': 0,
      'fill-extrusion-opacity': 0.45
    }
  })
}

function applyViewMode(mode) {
  if (!mapInstance || !mapLoaded) {
    return
  }

  const is3d = mode === '3d'

  mapInstance.easeTo({
    pitch: is3d ? 60 : 0,
    bearing: is3d ? -28 : 0,
    duration: 900
  })

  if (mapInstance.getLayer('road-extrusions')) {
    mapInstance.setLayoutProperty('road-extrusions', 'visibility', is3d ? 'visible' : 'none')
  }

  mapRoot.value?.classList.toggle('mode-3d', is3d)
}

function syncMap() {
  if (!mapInstance || !mapLoaded) {
    return
  }

  ensureMapLayers()
  ensureExtrusionLayer()
  updateLayerVisibility()
  applyViewMode(viewMode.value)
  fitToBestBounds()
}

function setViewMode(mode) {
  viewMode.value = mode
}

function focusOnRoute() {
  fitToBestBounds()
}

onMounted(() => {
  mapInstance = new maplibregl.Map({
    container: mapRoot.value,
    style: buildMapStyle(),
    center: defaultCenter,
    zoom: 16,
    pitch: 0,
    bearing: 0,
    antialias: true
  })

  mapInstance.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), 'top-right')

  mapInstance.on('load', () => {
    mapLoaded = true
    syncMap()
  })
})

watch(
  () => [props.routeGeojson, props.facilities, props.layers, props.mapLayers],
  () => {
    syncMap()
  },
  { deep: true }
)

watch(viewMode, (mode) => {
  applyViewMode(mode)
})

onBeforeUnmount(() => {
  if (mapInstance) {
    mapInstance.remove()
    mapInstance = null
  }
})
</script>
