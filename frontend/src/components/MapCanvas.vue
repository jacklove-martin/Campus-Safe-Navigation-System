<template>
  <section class="panel map-panel">
    <div class="map-panel-top">
      <div>
        <p class="eyebrow">Live Spatial Canvas</p>
        <h2>校园空间态势图</h2>
      </div>
      <div class="toolbar-actions">
        <button class="mini-button active">路线总览</button>
        <button class="mini-button">设施联动</button>
        <button class="mini-button">风险提示</button>
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

    <div class="map-stage live-map-shell">
      <div ref="mapRoot" class="leaflet-host"></div>

      <div class="map-overlay-copy">
        <div class="map-overlay-badge">OpenStreetMap</div>
        <p>{{ summary.message }}</p>
      </div>

      <div class="route-summary-card editorial-card">
        <span class="route-tag">{{ summary.dataSource }}</span>
        <strong>{{ summary.mode }}</strong>
        <p>{{ summary.title }}</p>
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
import L from 'leaflet'
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
const defaultCenter = [30.458, 114.613]

let mapInstance = null
let routeLayer = null
let facilityLayer = null
let roadNetworkLayer = null
let hazardLayer = null
let assemblyLayer = null
let serviceFacilityLayer = null
let hasFitInitialData = false

const activeLayers = computed(() =>
  props.layers.reduce((acc, layer) => {
    acc[layer.id] = layer.active
    return acc
  }, {})
)

function clearLayer(layerRefName) {
  if (layerRefName === 'route' && routeLayer) {
    routeLayer.remove()
    routeLayer = null
  }

  if (layerRefName === 'facility' && facilityLayer) {
    facilityLayer.remove()
    facilityLayer = null
  }

  if (layerRefName === 'roadNetwork' && roadNetworkLayer) {
    roadNetworkLayer.remove()
    roadNetworkLayer = null
  }

  if (layerRefName === 'hazard' && hazardLayer) {
    hazardLayer.remove()
    hazardLayer = null
  }

  if (layerRefName === 'assembly' && assemblyLayer) {
    assemblyLayer.remove()
    assemblyLayer = null
  }

  if (layerRefName === 'serviceFacility' && serviceFacilityLayer) {
    serviceFacilityLayer.remove()
    serviceFacilityLayer = null
  }
}

function drawRoute() {
  clearLayer('route')

  if (!mapInstance || !props.routeGeojson?.geometry?.coordinates?.length) {
    return
  }

  routeLayer = L.geoJSON(props.routeGeojson, {
    style: {
      color: '#157b69',
      weight: 6,
      opacity: 0.92
    }
  }).addTo(mapInstance)

  const bounds = routeLayer.getBounds()
  if (bounds.isValid()) {
    mapInstance.fitBounds(bounds.pad(0.15))
  }
}

function drawRoadNetwork() {
  clearLayer('roadNetwork')

  if (!mapInstance || !activeLayers.value.roads || !props.mapLayers.roads?.features?.length) {
    return
  }

  roadNetworkLayer = L.geoJSON(props.mapLayers.roads, {
    style: (feature) => ({
      color: Number(feature.properties?.lighting_score ?? 8) < 5 ? '#cf9c3a' : '#6f90d9',
      weight: 2.5,
      opacity: 0.68
    }),
    onEachFeature: (feature, layer) => {
      layer.bindPopup(
        `<strong>${feature.properties?.road_name || '道路路段'}</strong><br>` +
          `长度：${Math.round(feature.properties?.length_m || 0)} 米<br>` +
          `照明评分：${feature.properties?.lighting_score ?? '暂无'}`
      )
    }
  }).addTo(mapInstance)
}

function drawHazards() {
  clearLayer('hazard')

  if (!mapInstance || !activeLayers.value.hazards || !props.mapLayers.hazards?.features?.length) {
    return
  }

  hazardLayer = L.geoJSON(props.mapLayers.hazards, {
    pointToLayer: (_feature, latlng) =>
      L.circleMarker(latlng, {
        radius: 8,
        color: '#ffffff',
        weight: 2,
        fillColor: '#ca6656',
        fillOpacity: 0.95
      }),
    onEachFeature: (feature, layer) => {
      layer.bindPopup(
        `<strong>风险路段</strong><br>` +
          `${feature.properties?.road_name || '未命名道路'}<br>` +
          `照明：${feature.properties?.lighting_score ?? '暂无'}，无障碍：${feature.properties?.barrier_free_score ?? '暂无'}`
      )
    }
  }).addTo(mapInstance)
}

function drawAssemblyPoints() {
  clearLayer('assembly')

  if (!mapInstance || !activeLayers.value.assembly || !props.mapLayers.assembly?.features?.length) {
    return
  }

  assemblyLayer = L.geoJSON(props.mapLayers.assembly, {
    pointToLayer: (_feature, latlng) =>
      L.circleMarker(latlng, {
        radius: 9,
        color: '#ffffff',
        weight: 2,
        fillColor: '#157b69',
        fillOpacity: 0.96
      }),
    onEachFeature: (feature, layer) => {
      layer.bindPopup(
        `<strong>${feature.properties?.name || '疏散点'}</strong><br>` +
          `${feature.properties?.category || ''}<br>` +
          `${feature.properties?.remark || '应急集合位置'}`
      )
    }
  }).addTo(mapInstance)
}

function drawServiceFacilities() {
  clearLayer('serviceFacility')

  if (!mapInstance || !activeLayers.value.facilities || !props.mapLayers.facilities?.features?.length) {
    return
  }

  serviceFacilityLayer = L.geoJSON(props.mapLayers.facilities, {
    pointToLayer: (feature, latlng) =>
      L.circleMarker(latlng, {
        radius: 5,
        color: '#ffffff',
        weight: 1.5,
        fillColor: feature.properties?.night_available ? '#df9f39' : '#6f90d9',
        fillOpacity: 0.9
      }),
    onEachFeature: (feature, layer) => {
      layer.bindPopup(
        `<strong>${feature.properties?.name || '服务设施'}</strong><br>` +
          `${feature.properties?.category || ''}<br>` +
          `${feature.properties?.night_available ? '夜间可用' : '常规时段'}`
      )
    }
  }).addTo(mapInstance)
}

function drawFacilities() {
  clearLayer('facility')

  if (!mapInstance || !activeLayers.value.facilities || !props.facilities.length) {
    return
  }

  const features = props.facilities
    .filter((item) => item.coordinate?.lng && item.coordinate?.lat)
    .map((item) => ({
      type: 'Feature',
      geometry: {
        type: 'Point',
        coordinates: [item.coordinate.lng, item.coordinate.lat]
      },
      properties: {
        name: item.facility_name,
        type: item.facility_type,
        status: item.night_available ? '夜间可用' : '常规时段',
        badge: item.is_evacuation_point ? '疏散点' : '设施'
      }
    }))

  if (!features.length) {
    return
  }

  facilityLayer = L.geoJSON(
    {
      type: 'FeatureCollection',
      features
    },
    {
      pointToLayer: (feature, latlng) =>
        L.circleMarker(latlng, {
          radius: 7,
          color: '#ffffff',
          weight: 2,
          fillColor: feature.properties.badge === '疏散点' ? '#ca6656' : '#6f90d9',
          fillOpacity: 0.95
        }),
      onEachFeature: (feature, layer) => {
        layer.bindPopup(
          `<strong>${feature.properties.name}</strong><br>${feature.properties.type}<br>${feature.properties.status}`
        )
      }
    }
  ).addTo(mapInstance)
}

function syncMapLayers() {
  if (!mapInstance) {
    return
  }

  drawRoadNetwork()
  drawHazards()
  drawAssemblyPoints()
  drawServiceFacilities()
  drawRoute()
  drawFacilities()

  if (!hasFitInitialData && roadNetworkLayer?.getBounds?.().isValid()) {
    mapInstance.fitBounds(roadNetworkLayer.getBounds().pad(0.12))
    hasFitInitialData = true
  } else if (!props.routeGeojson?.geometry?.coordinates?.length && !hasFitInitialData) {
    mapInstance.setView(defaultCenter, 16)
  }
}

onMounted(() => {
  mapInstance = L.map(mapRoot.value, {
    zoomControl: true,
    attributionControl: true
  }).setView(defaultCenter, 16)

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 20,
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(mapInstance)

  syncMapLayers()
})

watch(
  () => [props.routeGeojson, props.facilities, props.layers, props.mapLayers],
  () => {
    syncMapLayers()
  },
  { deep: true }
)

onBeforeUnmount(() => {
  if (mapInstance) {
    mapInstance.remove()
    mapInstance = null
  }
})
</script>
