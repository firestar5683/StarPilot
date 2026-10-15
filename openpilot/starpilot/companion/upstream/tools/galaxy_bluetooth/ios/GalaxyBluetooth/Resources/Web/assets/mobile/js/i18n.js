import { reactive } from "vue"

const STORAGE_KEY = "galaxy-language"

export const LANGUAGE_OPTIONS = [
  { value: "en", label: "English" },
  { value: "es", label: "Spanish" },
  { value: "fr", label: "French" },
  { value: "ko", label: "Korean" },
  { value: "zh-CHS", label: "Chinese" },
]

const SUPPORTED_CODES = new Set(LANGUAGE_OPTIONS.map((option) => option.value))

// Galaxy deliberately keeps English as the fallback. This lets new server-side
// labels ship safely before they have been added to every translation below.
const TRANSLATIONS = {
  es: {
    English: "Inglés", Spanish: "Español", French: "Francés", Korean: "Coreano", Chinese: "Chino",
    Home: "Inicio", Toggles: "Interruptores", Tools: "Herramientas", Recordings: "Grabaciones",
    Bluetooth: "Bluetooth", "Cameras & Monitoring": "Cámaras y monitoreo", Galaxy: "Galaxy",
    "Logs & Diagnostics": "Registros y diagnósticos", "Model Manager": "Administrador de modelos",
    "Navigation & Maps": "Navegación y mapas", "System Tools": "Herramientas del sistema",
    "Model Laboratory": "Laboratorio de modelos", Plots: "Gráficas", "Testing Ground": "Área de pruebas",
    "Theme Maker": "Creador de temas", "Tuning, Plots & Testing": "Ajustes, gráficas y pruebas",
    "Vehicle Controls": "Controles del vehículo", Main: "Principal", Offline: "Sin conexión", Parked: "Estacionado",
    Back: "Atrás", Menu: "Menú", "Galaxy home": "Inicio de Galaxy", "Search toggles...": "Buscar interruptores...",
    "Search toggles": "Buscar interruptores", "Clear search": "Borrar búsqueda", "Dark mode": "Modo oscuro",
    "Light mode": "Modo claro", "Switch to dark mode": "Cambiar a modo oscuro", "Switch to light mode": "Cambiar a modo claro",
    Settings: "Configuración", Language: "Idioma", "Select language": "Seleccionar idioma", Advanced: "Avanzado",
    "result(s)": "resultado(s)",
    "Galaxy uses English when no language is selected.": "Galaxy usa inglés si no se selecciona un idioma.",
    "Language updated.": "Idioma actualizado.", "Unable to save language.": "No se pudo guardar el idioma.",
    "Loading configuration...": "Cargando configuración...", "No settings available.": "No hay ajustes disponibles.",
    "No settings in this section.": "No hay ajustes en esta sección.", "Locked:": "Bloqueado:", "Step:": "Paso:",
    "This setting can only be changed while parked.": "Este ajuste solo se puede cambiar mientras el vehículo está estacionado.",
    Default: "Predeterminado", "Loading...": "Cargando...", "No options available": "No hay opciones disponibles",
    "Working...": "Procesando...", Run: "Ejecutar", Manage: "Administrar", Close: "Cerrar", Stock: "Original",
  },
  fr: {
    English: "Anglais", Spanish: "Espagnol", French: "Français", Korean: "Coréen", Chinese: "Chinois",
    Home: "Accueil", Toggles: "Options", Tools: "Outils", Recordings: "Enregistrements",
    Bluetooth: "Bluetooth", "Cameras & Monitoring": "Caméras et surveillance", Galaxy: "Galaxy",
    "Logs & Diagnostics": "Journaux et diagnostics", "Model Manager": "Gestionnaire de modèles",
    "Navigation & Maps": "Navigation et cartes", "System Tools": "Outils système",
    "Model Laboratory": "Laboratoire de modèles", Plots: "Graphiques", "Testing Ground": "Zone de test",
    "Theme Maker": "Créateur de thèmes", "Tuning, Plots & Testing": "Réglages, graphiques et tests",
    "Vehicle Controls": "Commandes du véhicule", Main: "Principal", Offline: "Hors ligne", Parked: "Stationné",
    Back: "Retour", Menu: "Menu", "Galaxy home": "Accueil Galaxy", "Search toggles...": "Rechercher des options...",
    "Search toggles": "Rechercher des options", "Clear search": "Effacer la recherche", "Dark mode": "Mode sombre",
    "Light mode": "Mode clair", "Switch to dark mode": "Passer au mode sombre", "Switch to light mode": "Passer au mode clair",
    Settings: "Paramètres", Language: "Langue", "Select language": "Choisir la langue", Advanced: "Avancé",
    "result(s)": "résultat(s)",
    "Galaxy uses English when no language is selected.": "Galaxy utilise l’anglais si aucune langue n’est sélectionnée.",
    "Language updated.": "Langue mise à jour.", "Unable to save language.": "Impossible d’enregistrer la langue.",
    "Loading configuration...": "Chargement de la configuration...", "No settings available.": "Aucun réglage disponible.",
    "No settings in this section.": "Aucun réglage dans cette section.", "Locked:": "Verrouillé :", "Step:": "Pas :",
    "This setting can only be changed while parked.": "Ce réglage ne peut être modifié que lorsque le véhicule est stationné.",
    Default: "Par défaut", "Loading...": "Chargement...", "No options available": "Aucune option disponible",
    "Working...": "En cours...", Run: "Exécuter", Manage: "Gérer", Close: "Fermer", Stock: "Origine",
  },
  ko: {
    English: "영어", Spanish: "스페인어", French: "프랑스어", Korean: "한국어", Chinese: "중국어",
    Home: "홈", Toggles: "토글", Tools: "도구", Recordings: "녹화",
    Bluetooth: "블루투스", "Cameras & Monitoring": "카메라 및 모니터링", Galaxy: "Galaxy",
    "Logs & Diagnostics": "로그 및 진단", "Model Manager": "모델 관리자",
    "Navigation & Maps": "내비게이션 및 지도", "System Tools": "시스템 도구",
    "Model Laboratory": "모델 연구소", Plots: "플롯", "Testing Ground": "테스트 공간",
    "Theme Maker": "테마 만들기", "Tuning, Plots & Testing": "튜닝, 플롯 및 테스트",
    "Vehicle Controls": "차량 제어", Main: "메인", Offline: "오프라인", Parked: "주차됨",
    Back: "뒤로", Menu: "메뉴", "Galaxy home": "Galaxy 홈", "Search toggles...": "토글 검색...",
    "Search toggles": "토글 검색", "Clear search": "검색 지우기", "Dark mode": "다크 모드",
    "Light mode": "라이트 모드", "Switch to dark mode": "다크 모드로 전환", "Switch to light mode": "라이트 모드로 전환",
    Settings: "설정", Language: "언어", "Select language": "언어 선택", Advanced: "고급",
    "result(s)": "개 결과",
    "Galaxy uses English when no language is selected.": "언어를 선택하지 않으면 Galaxy는 영어를 사용합니다.",
    "Language updated.": "언어가 업데이트되었습니다.", "Unable to save language.": "언어를 저장할 수 없습니다.",
    "Loading configuration...": "설정을 불러오는 중...", "No settings available.": "사용 가능한 설정이 없습니다.",
    "No settings in this section.": "이 섹션에 설정이 없습니다.", "Locked:": "잠김:", "Step:": "단계:",
    "This setting can only be changed while parked.": "이 설정은 주차 중에만 변경할 수 있습니다.",
    Default: "기본값", "Loading...": "로드 중...", "No options available": "사용 가능한 옵션이 없습니다",
    "Working...": "처리 중...", Run: "실행", Manage: "관리", Close: "닫기", Stock: "기본",
  },
  "zh-CHS": {
    English: "英语", Spanish: "西班牙语", French: "法语", Korean: "韩语", Chinese: "中文",
    Home: "主页", Toggles: "开关", Tools: "工具", Recordings: "录制内容",
    Bluetooth: "蓝牙", "Cameras & Monitoring": "摄像头和监控", Galaxy: "Galaxy",
    "Logs & Diagnostics": "日志和诊断", "Model Manager": "模型管理器",
    "Navigation & Maps": "导航和地图", "System Tools": "系统工具",
    "Model Laboratory": "模型实验室", Plots: "图表", "Testing Ground": "测试区",
    "Theme Maker": "主题制作器", "Tuning, Plots & Testing": "调校、图表和测试",
    "Vehicle Controls": "车辆控制", Main: "主菜单", Offline: "离线", Parked: "已停车",
    Back: "返回", Menu: "菜单", "Galaxy home": "Galaxy 主页", "Search toggles...": "搜索开关...",
    "Search toggles": "搜索开关", "Clear search": "清除搜索", "Dark mode": "深色模式",
    "Light mode": "浅色模式", "Switch to dark mode": "切换到深色模式", "Switch to light mode": "切换到浅色模式",
    Settings: "设置", Language: "语言", "Select language": "选择语言", Advanced: "高级",
    "result(s)": "个结果",
    "Galaxy uses English when no language is selected.": "未选择语言时，Galaxy 将使用英语。",
    "Language updated.": "语言已更新。", "Unable to save language.": "无法保存语言。",
    "Loading configuration...": "正在加载配置...", "No settings available.": "没有可用设置。",
    "No settings in this section.": "此部分没有设置。", "Locked:": "已锁定：", "Step:": "步长：",
    "This setting can only be changed while parked.": "此设置只能在车辆停放时更改。",
    Default: "默认值", "Loading...": "加载中...", "No options available": "没有可用选项",
    "Working...": "处理中...", Run: "运行", Manage: "管理", Close: "关闭", Stock: "原厂",
  },
}

// The settings catalog is shared with the native UI, so most of its labels
// arrive from the device rather than this bundle. These common section names
// and controls keep the Galaxy settings screen translated as well.
const MORE_TRANSLATIONS = {
  es: {
    Favorites: "Favoritos", "Lateral (Steering)": "Lateral (Dirección)",
    "Longitudinal (Speed & Following)": "Longitudinal (Velocidad y seguimiento)",
    "Vision Speed Limits": "Límites de velocidad por visión", "Visual (Display & UI)": "Visual (Pantalla e interfaz)",
    "Sounds & Alerts": "Sonidos y alertas", Vehicle: "Vehículo", "Wheel Controls": "Controles del volante",
    "Device & Data": "Dispositivo y datos", Developer: "Desarrollador", "Advanced Lateral Tuning": "Ajuste lateral avanzado",
    "Advanced steering control changes to fine-tune how openpilot drives.": "Cambios avanzados en el control de la dirección para ajustar cómo conduce openpilot.",
    "Always On Lateral": "Lateral siempre activo", "openpilot's steering remains active even when the accelerator or brake pedals are pressed.": "La dirección de openpilot permanece activa incluso cuando se pisan el acelerador o los frenos.",
    "Lane Changes": "Cambios de carril", "Allow openpilot to change lanes.": "Permitir que openpilot cambie de carril.",
    "Lateral Tuning": "Ajuste lateral", "Miscellaneous steering control changes to fine-tune how openpilot drives.": "Cambios diversos del control de la dirección para ajustar cómo conduce openpilot.",
    "Quality of Life": "Calidad de vida", "Steering control changes to fine-tune how openpilot drives.": "Cambios del control de la dirección para ajustar cómo conduce openpilot.",
    "Enable V-ASM": "Activar V-ASM", "Favorites": "Favoritos", "Device & Data": "Dispositivo y datos",
    Routes: "Rutas", Route: "Ruta", Selected: "Seleccionada", Recommended: "Recomendada", Alternative: "Alternativa", Select: "Seleccionar", "Choose a route": "Elegir una ruta",
  },
  fr: {
    Favorites: "Favoris", "Lateral (Steering)": "Latéral (Direction)",
    "Longitudinal (Speed & Following)": "Longitudinal (Vitesse et suivi)",
    "Vision Speed Limits": "Limites de vitesse par vision", "Visual (Display & UI)": "Visuel (Affichage et interface)",
    "Sounds & Alerts": "Sons et alertes", Vehicle: "Véhicule", "Wheel Controls": "Commandes au volant",
    "Device & Data": "Appareil et données", Developer: "Développeur", "Advanced Lateral Tuning": "Réglage latéral avancé",
    "Advanced steering control changes to fine-tune how openpilot drives.": "Modifications avancées de la direction pour régler finement le comportement d’openpilot.",
    "Always On Lateral": "Direction latérale toujours active", "openpilot's steering remains active even when the accelerator or brake pedals are pressed.": "La direction d’openpilot reste active même lorsque l’accélérateur ou les freins sont enfoncés.",
    "Lane Changes": "Changements de voie", "Allow openpilot to change lanes.": "Autoriser openpilot à changer de voie.",
    "Lateral Tuning": "Réglage latéral", "Miscellaneous steering control changes to fine-tune how openpilot drives.": "Divers réglages de direction pour ajuster finement le comportement d’openpilot.",
    "Quality of Life": "Confort d’utilisation", "Steering control changes to fine-tune how openpilot drives.": "Réglages de direction pour ajuster finement le comportement d’openpilot.",
    "Enable V-ASM": "Activer V-ASM",
    Routes: "Itinéraires", Route: "Itinéraire", Selected: "Sélectionné", Recommended: "Recommandé", Alternative: "Alternative", Select: "Sélectionner", "Choose a route": "Choisir un itinéraire",
  },
  ko: {
    Favorites: "즐겨찾기", "Lateral (Steering)": "횡방향 (조향)",
    "Longitudinal (Speed & Following)": "종방향 (속도 및 추종)",
    "Vision Speed Limits": "비전 속도 제한", "Visual (Display & UI)": "시각 (디스플레이 및 UI)",
    "Sounds & Alerts": "소리 및 경고", Vehicle: "차량", "Wheel Controls": "휠 컨트롤",
    "Device & Data": "장치 및 데이터", Developer: "개발자", "Advanced Lateral Tuning": "고급 횡방향 튜닝",
    "Advanced steering control changes to fine-tune how openpilot drives.": "openpilot의 주행 방식을 세밀하게 조정하는 고급 조향 제어 변경입니다.",
    "Always On Lateral": "항상 활성화된 횡방향 제어", "openpilot's steering remains active even when the accelerator or brake pedals are pressed.": "가속 페달이나 브레이크 페달을 밟아도 openpilot 조향이 계속 활성화됩니다.",
    "Lane Changes": "차선 변경", "Allow openpilot to change lanes.": "openpilot이 차선을 변경하도록 허용합니다.",
    "Lateral Tuning": "횡방향 튜닝", "Miscellaneous steering control changes to fine-tune how openpilot drives.": "openpilot의 주행을 세밀하게 조정하는 기타 조향 제어 변경입니다.",
    "Quality of Life": "편의 기능", "Steering control changes to fine-tune how openpilot drives.": "openpilot의 주행을 세밀하게 조정하는 조향 제어 변경입니다.",
    "Enable V-ASM": "V-ASM 활성화",
    Routes: "경로", Route: "경로", Selected: "선택됨", Recommended: "추천", Alternative: "대안", Select: "선택", "Choose a route": "경로 선택",
  },
  "zh-CHS": {
    Favorites: "收藏", "Lateral (Steering)": "横向（转向）",
    "Longitudinal (Speed & Following)": "纵向（速度和跟车）", "Vision Speed Limits": "视觉限速",
    "Visual (Display & UI)": "视觉（显示和界面）", "Sounds & Alerts": "声音和提醒", Vehicle: "车辆",
    "Wheel Controls": "方向盘控制", "Device & Data": "设备和数据", Developer: "开发者", "Advanced Lateral Tuning": "高级横向调校",
    "Advanced steering control changes to fine-tune how openpilot drives.": "用于精细调整 openpilot 驾驶方式的高级转向控制设置。",
    "Always On Lateral": "始终启用横向控制", "openpilot's steering remains active even when the accelerator or brake pedals are pressed.": "即使踩下加速或制动踏板，openpilot 转向仍保持启用。",
    "Lane Changes": "变道", "Allow openpilot to change lanes.": "允许 openpilot 变道。", "Lateral Tuning": "横向调校",
    "Miscellaneous steering control changes to fine-tune how openpilot drives.": "用于精细调整 openpilot 驾驶方式的其他转向控制设置。",
    "Quality of Life": "使用体验", "Steering control changes to fine-tune how openpilot drives.": "用于精细调整 openpilot 驾驶方式的转向控制设置。",
    "Enable V-ASM": "启用 V-ASM",
    Routes: "路线", Route: "路线", Selected: "已选择", Recommended: "推荐", Alternative: "备选", Select: "选择", "Choose a route": "选择路线",
  },
}

Object.keys(MORE_TRANSLATIONS).forEach((code) => Object.assign(TRANSLATIONS[code], MORE_TRANSLATIONS[code]))

// A word-level fallback covers the many device-provided descriptions and the
// older Galaxy views that still contain literal English labels. Exact phrases
// above always win; this fallback only runs for a non-English selection.
const TERM_TRANSLATIONS = {
  es: {
    "Advanced": "Avanzado", "Always On": "Siempre activo", "Lateral": "Lateral", "Steering": "Dirección", "Longitudinal": "Longitudinal", "Speed": "Velocidad", "Following": "Seguimiento", "Vision": "Visión", "Limits": "Límites", "Visual": "Visual", "Display": "Pantalla", "Sounds": "Sonidos", "Alerts": "Alertas", "Vehicle": "Vehículo", "Wheel": "Volante", "Controls": "Controles", "Device": "Dispositivo", "Data": "Datos", "Developer": "Desarrollador", "Favorites": "Favoritos", "Main": "Principal", "Tools": "Herramientas", "Recordings": "Grabaciones", "Cameras": "Cámaras", "Monitoring": "monitoreo", "Logs": "Registros", "Diagnostics": "diagnósticos", "Model": "Modelo", "Manager": "administrador", "Navigation": "Navegación", "Maps": "mapas", "System": "Sistema", "Laboratory": "Laboratorio", "Plots": "Gráficas", "Testing": "Pruebas", "Ground": "Área", "Theme": "Tema", "Maker": "creador", "Home": "Inicio", "Toggles": "Interruptores", "Install": "Instalar", "Update": "Actualizar", "Available": "disponible", "Loading": "Cargando", "Error": "Error", "Retry": "Reintentar", "Save": "Guardar", "Cancel": "Cancelar", "Close": "Cerrar", "Delete": "Eliminar", "All": "todo", "Search": "Buscar", "Clear": "Borrar", "Manage": "Administrar", "Connected": "Conectado", "Disconnect": "Desconectar", "Connect": "Conectar", "Pair": "Emparejar", "Refresh": "Actualizar", "Status": "Estado", "Samples": "Muestras", "Duration": "Duración", "Distance": "Distancia", "drives": "viajes", "hours": "horas", "engaged": "activado", "Onroad": "En carretera", "Offroad": "Fuera de carretera", "Enabled": "Activado", "Disabled": "Desactivado", "Default": "Predeterminado", "Working": "Procesando", "Run": "Ejecutar", "Reset": "Restablecer", "Download": "Descargar", "Network": "Red", "Current": "Actual", "Change": "Cambiar", "Changes": "Cambios", "Allow": "Permitir", "Use": "Usar", "Show": "Mostrar", "Hide": "Ocultar", "Enable": "Activar", "Disable": "Desactivar", "Automatic": "Automático", "Settings": "Configuración", "Language": "Idioma", "Routes": "Rutas", "Selected": "Seleccionada", "Recommended": "Recomendada", "Alternative": "Alternativa",
  },
  fr: {
    "Advanced": "Avancé", "Always On": "Toujours actif", "Lateral": "Latéral", "Steering": "Direction", "Longitudinal": "Longitudinal", "Speed": "Vitesse", "Following": "Suivi", "Vision": "Vision", "Limits": "Limites", "Visual": "Visuel", "Display": "Affichage", "Sounds": "Sons", "Alerts": "Alertes", "Vehicle": "Véhicule", "Wheel": "Volant", "Controls": "Commandes", "Device": "Appareil", "Data": "Données", "Developer": "Développeur", "Favorites": "Favoris", "Main": "Principal", "Tools": "Outils", "Recordings": "Enregistrements", "Cameras": "Caméras", "Monitoring": "surveillance", "Logs": "Journaux", "Diagnostics": "diagnostics", "Model": "Modèle", "Manager": "gestionnaire", "Navigation": "Navigation", "Maps": "cartes", "System": "Système", "Laboratory": "Laboratoire", "Plots": "Graphiques", "Testing": "Tests", "Ground": "Zone", "Theme": "Thème", "Maker": "créateur", "Home": "Accueil", "Toggles": "Options", "Install": "Installer", "Update": "Mettre à jour", "Available": "disponible", "Loading": "Chargement", "Error": "Erreur", "Retry": "Réessayer", "Save": "Enregistrer", "Cancel": "Annuler", "Close": "Fermer", "Delete": "Supprimer", "All": "tout", "Search": "Rechercher", "Clear": "Effacer", "Manage": "Gérer", "Connected": "Connecté", "Disconnect": "Déconnecter", "Connect": "Connecter", "Pair": "Associer", "Refresh": "Actualiser", "Status": "État", "Samples": "Échantillons", "Duration": "Durée", "Distance": "Distance", "drives": "trajets", "hours": "heures", "engaged": "activé", "Onroad": "En route", "Offroad": "Hors route", "Enabled": "Activé", "Disabled": "Désactivé", "Default": "Par défaut", "Working": "En cours", "Run": "Exécuter", "Reset": "Réinitialiser", "Download": "Télécharger", "Network": "Réseau", "Current": "Actuel", "Change": "Modifier", "Changes": "Modifications", "Allow": "Autoriser", "Use": "Utiliser", "Show": "Afficher", "Hide": "Masquer", "Enable": "Activer", "Disable": "Désactiver", "Automatic": "Automatique", "Settings": "Paramètres", "Language": "Langue", "Routes": "Itinéraires", "Selected": "Sélectionné", "Recommended": "Recommandé", "Alternative": "Alternative",
  },
  ko: {
    "Advanced": "고급", "Always On": "항상 활성화", "Lateral": "횡방향", "Steering": "조향", "Longitudinal": "종방향", "Speed": "속도", "Following": "추종", "Vision": "비전", "Limits": "제한", "Visual": "시각", "Display": "디스플레이", "Sounds": "소리", "Alerts": "경고", "Vehicle": "차량", "Wheel": "휠", "Controls": "제어", "Device": "장치", "Data": "데이터", "Developer": "개발자", "Favorites": "즐겨찾기", "Main": "메인", "Tools": "도구", "Recordings": "녹화", "Cameras": "카메라", "Monitoring": "모니터링", "Logs": "로그", "Diagnostics": "진단", "Model": "모델", "Manager": "관리자", "Navigation": "내비게이션", "Maps": "지도", "System": "시스템", "Laboratory": "연구소", "Plots": "플롯", "Testing": "테스트", "Ground": "공간", "Theme": "테마", "Maker": "제작", "Home": "홈", "Toggles": "토글", "Install": "설치", "Update": "업데이트", "Available": "사용 가능", "Loading": "로드 중", "Error": "오류", "Retry": "재시도", "Save": "저장", "Cancel": "취소", "Close": "닫기", "Delete": "삭제", "All": "모두", "Search": "검색", "Clear": "지우기", "Manage": "관리", "Connected": "연결됨", "Disconnect": "연결 해제", "Connect": "연결", "Pair": "페어링", "Refresh": "새로 고침", "Status": "상태", "Samples": "샘플", "Duration": "시간", "Distance": "거리", "drives": "주행", "hours": "시간", "engaged": "활성화", "Onroad": "주행 중", "Offroad": "오프로드", "Enabled": "활성화", "Disabled": "비활성화", "Default": "기본값", "Working": "처리 중", "Run": "실행", "Reset": "초기화", "Download": "다운로드", "Network": "네트워크", "Current": "현재", "Change": "변경", "Changes": "변경 사항", "Allow": "허용", "Use": "사용", "Show": "표시", "Hide": "숨기기", "Enable": "활성화", "Disable": "비활성화", "Automatic": "자동", "Settings": "설정", "Language": "언어", "Routes": "경로", "Selected": "선택됨", "Recommended": "추천", "Alternative": "대안",
  },
  "zh-CHS": {
    "Advanced": "高级", "Always On": "始终启用", "Lateral": "横向", "Steering": "转向", "Longitudinal": "纵向", "Speed": "速度", "Following": "跟车", "Vision": "视觉", "Limits": "限制", "Visual": "视觉", "Display": "显示", "Sounds": "声音", "Alerts": "提醒", "Vehicle": "车辆", "Wheel": "方向盘", "Controls": "控制", "Device": "设备", "Data": "数据", "Developer": "开发者", "Favorites": "收藏", "Main": "主菜单", "Tools": "工具", "Recordings": "录制", "Cameras": "摄像头", "Monitoring": "监控", "Logs": "日志", "Diagnostics": "诊断", "Model": "模型", "Manager": "管理器", "Navigation": "导航", "Maps": "地图", "System": "系统", "Laboratory": "实验室", "Plots": "图表", "Testing": "测试", "Ground": "区域", "Theme": "主题", "Maker": "制作器", "Home": "主页", "Toggles": "开关", "Install": "安装", "Update": "更新", "Available": "可用", "Loading": "加载中", "Error": "错误", "Retry": "重试", "Save": "保存", "Cancel": "取消", "Close": "关闭", "Delete": "删除", "All": "全部", "Search": "搜索", "Clear": "清除", "Manage": "管理", "Connected": "已连接", "Disconnect": "断开连接", "Connect": "连接", "Pair": "配对", "Refresh": "刷新", "Status": "状态", "Samples": "样本", "Duration": "时长", "Distance": "距离", "drives": "驾驶次数", "hours": "小时", "engaged": "已启用", "Onroad": "行驶中", "Offroad": "非行驶", "Enabled": "已启用", "Disabled": "已停用", "Default": "默认", "Working": "处理中", "Run": "运行", "Reset": "重置", "Download": "下载", "Network": "网络", "Current": "当前", "Change": "更改", "Changes": "更改内容", "Allow": "允许", "Use": "使用", "Show": "显示", "Hide": "隐藏", "Enable": "启用", "Disable": "停用", "Automatic": "自动", "Settings": "设置", "Language": "语言", "Routes": "路线", "Selected": "已选择", "Recommended": "推荐", "Alternative": "备选",
  },
}

Object.assign(TERM_TRANSLATIONS.es, { Route: "Ruta", Select: "Seleccionar" })
Object.assign(TERM_TRANSLATIONS.fr, { Route: "Itinéraire", Select: "Sélectionner" })
Object.assign(TERM_TRANSLATIONS.ko, { Route: "경로", Select: "선택" })
Object.assign(TERM_TRANSLATIONS["zh-CHS"], { Route: "路线", Select: "选择" })

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
}

const TERM_REPLACERS = Object.fromEntries(Object.entries(TERM_TRANSLATIONS).map(([code, terms]) => [
  code,
  Object.entries(terms)
    .sort(([a], [b]) => b.length - a.length)
    .map(([source, target]) => [new RegExp(`(^|[^A-Za-z])${escapeRegExp(source)}(?=$|[^A-Za-z])`, "gi"), target, source.match(/[A-Za-z]+/g)?.length || 1]),
]))

function translateText(value) {
  const source = String(value ?? "")
  const exact = TRANSLATIONS[languageState?.code]?.[source]
  if (exact) return exact
  if (!languageState || languageState.code === "en" || /https?:\/\//i.test(source)) return source
  let translated = source
  let replacedWords = 0
  for (const [pattern, replacement, wordCount] of TERM_REPLACERS[languageState.code] || []) {
    translated = translated.replace(pattern, (_, prefix) => {
      replacedWords += wordCount
      return `${prefix}${replacement}`
    })
  }
  const sourceWords = source.match(/[A-Za-z]+/g)?.length || 0
  return sourceWords >= 4 && replacedWords / sourceWords < 0.8 ? source : translated
}

function storageValue() {
  try { return window.localStorage.getItem(STORAGE_KEY) || "en" } catch (e) { return "en" }
}

export function normalizeLanguage(value) {
  const code = String(value || "").trim().replace(/^main_/i, "")
  return SUPPORTED_CODES.has(code) ? code : "en"
}

export const languageState = reactive({ code: normalizeLanguage(storageValue()) })

const translatedTextNodes = new WeakMap()
const translatedAttributes = new WeakMap()
let domObserver = null
const TRANSLATABLE_ATTRIBUTES = ["aria-label", "placeholder", "title"]

function canTranslateNode(node) {
  const parent = node?.parentElement
  return !!parent && !parent.closest("script, style, textarea, pre, [data-no-translate]")
}

function translateTextNode(node) {
  if (!canTranslateNode(node)) return
  const current = node.nodeValue || ""
  if (!current.trim()) return
  let state = translatedTextNodes.get(node)
  if (!state) {
    state = { source: current, output: current }
    translatedTextNodes.set(node, state)
  } else if (current !== state.output) {
    // Vue replaced the source text (for example, a device-provided label).
    state.source = current
  }
  const output = translateText(state.source)
  if (output !== current) node.nodeValue = output
  state.output = output
}

function translateElementAttributes(element) {
  if (!element || element.matches("script, style, textarea, pre, [data-no-translate]")) return
  let state = translatedAttributes.get(element)
  if (!state) {
    state = {}
    translatedAttributes.set(element, state)
  }
  for (const attribute of TRANSLATABLE_ATTRIBUTES) {
    if (!element.hasAttribute(attribute)) continue
    const current = element.getAttribute(attribute) || ""
    const previous = state[attribute]
    if (!previous) state[attribute] = { source: current, output: current }
    else if (current !== previous.output) previous.source = current
    const entry = state[attribute]
    const output = translateText(entry.source)
    if (output !== current) element.setAttribute(attribute, output)
    entry.output = output
  }
}

export function translateDom(root = (typeof document !== "undefined" ? document.getElementById("galaxy-app") : null)) {
  if (!root || typeof document === "undefined") return
  translateElementAttributes(root)
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT)
  let node
  while ((node = walker.nextNode())) translateTextNode(node)
  root.querySelectorAll("*").forEach(translateElementAttributes)
}

export function installDomTranslator(root = (typeof document !== "undefined" ? document.getElementById("galaxy-app") : null)) {
  if (!root || typeof MutationObserver === "undefined") return
  translateDom(root)
  domObserver?.disconnect()
  domObserver = new MutationObserver((records) => {
    for (const record of records) {
      if (record.type === "characterData") translateTextNode(record.target)
      else if (record.type === "attributes") translateElementAttributes(record.target)
      else record.addedNodes.forEach((node) => {
        if (node.nodeType === Node.TEXT_NODE) translateTextNode(node)
        else if (node.nodeType === Node.ELEMENT_NODE) translateDom(node)
      })
    }
  })
  domObserver.observe(root, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: TRANSLATABLE_ATTRIBUTES })
}

export function setLanguage(value) {
  const code = normalizeLanguage(value)
  languageState.code = code
  try { window.localStorage.setItem(STORAGE_KEY, code) } catch (e) { /* storage can be unavailable in private webviews */ }
  if (typeof document !== "undefined") document.documentElement.lang = code === "zh-CHS" ? "zh-CN" : code
  if (typeof document !== "undefined") translateDom(document.getElementById("galaxy-app"))
  return code
}

export function t(key, fallback = key) {
  const source = String(key ?? "")
  const translated = translateText(source)
  return translated !== source ? translated : fallback || source
}

setLanguage(languageState.code)
