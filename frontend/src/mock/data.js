export const routeModes = [
  { id: 'night', label: '夜间安全', icon: 'Moon', accent: 'teal', description: '优先照明连续、开敞度更高的主通路' },
  { id: 'accessible', label: '无障碍', icon: 'Access', accent: 'gold', description: '避开台阶与陡坡，保障轮椅可达性' },
  { id: 'evacuation', label: '应急疏散', icon: 'Alert', accent: 'coral', description: '面向突发场景，优先最近安全集结点' },
  { id: 'multi', label: '多目标导航', icon: 'Flow', accent: 'sky', description: '支持食堂、商店、宿舍串联路径规划' }
]

export const quickQuestions = [
  '晚上从教学楼回一组团四栋哪条路更安全？',
  '现在最近还开门的食堂在哪里？',
  '从图书馆去操场的无障碍路线怎么走？',
  '如果宿舍楼发生火灾，怎么疏散到最近校门？'
]

export const mapLayers = [
  { id: 'roads', label: '道路网络', hint: '步行主路与支路', active: true },
  { id: 'lights', label: '夜间照明', hint: '路灯覆盖与弱照区', active: true },
  { id: 'facilities', label: '服务设施', hint: '食堂、图书馆、宿舍、校门', active: true },
  { id: 'hazards', label: '风险点位', hint: '围挡、施工、障碍点', active: true },
  { id: 'assembly', label: '疏散节点', hint: '操场、校门、应急出口', active: true }
]

export const liveStats = [
  { label: '当前模式', value: '夜间安全', tone: 'teal' },
  { label: '推荐路线', value: '3 条候选', tone: 'sky' },
  { label: '风险状态', value: '1 处施工绕行', tone: 'coral' },
  { label: '开放设施', value: '12 处可用', tone: 'gold' }
]

export const routeTimeline = [
  { time: '00:00', title: '教学楼北门出发', detail: '进入主步道，照明完整，通行宽度较好。', state: 'start' },
  { time: '02:10', title: '图书馆前广场', detail: '系统规避西侧围挡，转入中心广场路线。', state: 'normal' },
  { time: '04:30', title: '宿舍区主路', detail: '沿值班点与连续路灯区域前行，安全评分提升。', state: 'safe' },
  { time: '08:00', title: '到达一组团四栋', detail: '路径结束，可切换返程或周边设施推荐。', state: 'end' }
]

export const facilityCards = [
  {
    name: '第一食堂',
    type: '食堂',
    status: '营业中',
    badge: '夜宵',
    detail: '提供夜宵窗口，距离当前路径 180 米，适合返宿前顺路前往。'
  },
  {
    name: '图书馆东侧便利店',
    type: '便利店',
    status: '22:30 关门',
    badge: '文具',
    detail: '支持饮料、零食和文具购买，可作为多目标导航中途点。'
  },
  {
    name: '东门集结点',
    type: '应急点',
    status: '可达',
    badge: '疏散',
    detail: '适合火灾或突发事件时作为最近疏散目标点。'
  }
]

export const resultSummary = {
  title: '教学楼北门 → 一组团四栋',
  mode: '夜间安全路径',
  eta: '8 分钟',
  distance: '640 米',
  score: '安全评分 92',
  message: '当前为前端默认展示数据，后端连接成功后会自动覆盖。',
  dataSource: 'Mock Data',
  originLabel: '教学楼北门',
  midpointLabel: '图书馆广场',
  facilityLabel: '第一食堂',
  destinationLabel: '一组团四栋',
  poiLabel: '东门集结点',
  hazardLabel: '施工围挡',
  reason: [
    '优先通过主照明步道与开敞广场，降低夜间盲区风险。',
    '自动避开施工围挡、狭窄路口和照度偏低支路。',
    '沿线经过图书馆广场与宿舍值班区域，整体可视与求助条件更优。'
  ],
  steps: [
    '从教学楼北门出发，沿中轴主步道向东。',
    '经过图书馆前广场，绕开西侧施工围挡。',
    '转入宿舍区主路，沿连续照明区域前行。',
    '到达一组团四栋宿舍入口。'
  ]
}

export const alerts = [
  { level: '正常', title: '夜间照明稳定', text: '主步道照明覆盖良好，当前推荐路线安全等级较高。' },
  { level: '提示', title: '西侧施工绕行', text: '施工围挡区域已被剔除，建议不要脱离推荐路线。' },
  { level: '应急', title: '疏散模式可切换', text: '如遇突发情况，可一键切换至最近校门或操场。' }
]

export const scenarioCards = [
  { title: '晚间返宿', subtitle: '更安全的回宿路线', accent: 'teal' },
  { title: '无障碍通行', subtitle: '适合轮椅与行动不便用户', accent: 'gold' },
  { title: '突发疏散', subtitle: '校门与操场应急路径', accent: 'coral' }
]
