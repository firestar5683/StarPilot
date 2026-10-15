package link.firestar.companion

import android.animation.ValueAnimator
import android.app.Activity
import android.content.Context
import android.content.res.ColorStateList
import android.graphics.*
import android.graphics.drawable.GradientDrawable
import android.graphics.drawable.RippleDrawable
import android.text.InputType
import android.text.TextUtils
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.view.animation.LinearInterpolator
import android.view.inputmethod.EditorInfo
import android.widget.*
import kotlin.math.cos
import kotlin.math.roundToInt
import kotlin.math.sin

/** Connections in the order Automatic tries them. */
enum class Route(val title: String, val icon: Int) {
    GALAXY_WIFI("Galaxy Wi-Fi", R.drawable.ic_route_wifi),
    HOME_NETWORK("Home network", R.drawable.ic_route_lan),
    BLUETOOTH("Bluetooth", R.drawable.ic_route_bluetooth),
}

enum class RouteState { IDLE, UNAVAILABLE, TRYING, FAILED, LIVE }

/** Galaxy web tokens, so the native screens hand off to the web app without a seam. */
object Palette {
    const val SPACE = 0xFF070712.toInt()
    const val SURFACE = 0xFF110E1F.toInt()
    const val VIOLET = 0xFF9D72FF.toInt()
    const val VIOLET_SOFT = 0xFFC9B3FF.toInt()
    const val CYAN = 0xFF4DE8E8.toInt()
    const val ON = 0xFFF3F2F8.toInt()
    const val MUTED = 0xFF9D9BB8.toInt()
    const val ERROR = 0xFFFF5277.toInt()
    const val LINE = 0x1FFFFFFF
    fun of(state: RouteState) = when (state) {
        RouteState.IDLE -> ON
        RouteState.UNAVAILABLE -> MUTED
        RouteState.TRYING -> VIOLET_SOFT
        RouteState.FAILED -> ERROR
        RouteState.LIVE -> CYAN
    }
    fun alpha(color: Int, alpha: Int) = (color and 0x00FFFFFF) or (alpha.coerceIn(0, 255) shl 24)
    val condensed: Typeface = Typeface.create("sans-serif-condensed", Typeface.BOLD)
    val medium: Typeface = Typeface.create("sans-serif-medium", Typeface.NORMAL)
}

/** comma at the centre, one tilted orbit per connection. The orbit being tried carries a moving comet. */
class OrbitView(context: Context) : View(context) {
    private val dp = resources.displayMetrics.density
    private val states = Array(Route.entries.size) { RouteState.IDLE }
    private val icons = Route.entries.map { context.getDrawable(it.icon)!!.mutate() }
    private val core = BitmapFactory.decodeResource(resources, R.drawable.galaxy)
    private val tilt = floatArrayOf(-16f, 8f, -5f)
    private val reach = floatArrayOf(0.40f, 0.68f, 0.96f)
    private val anchor = floatArrayOf(200f, 330f, 105f)
    private val stroke = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.STROKE }
    private val fill = Paint(Paint.ANTI_ALIAS_FLAG)
    private val corePaint = Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG)
    private val dash = DashPathEffect(floatArrayOf(3 * dp, 5 * dp), 0f)
    private var glow: Shader? = null
    private var phase = 0f
    private val spin = ValueAnimator.ofFloat(0f, 1f).apply {
        duration = 2600; repeatCount = ValueAnimator.INFINITE; interpolator = LinearInterpolator()
        addUpdateListener { phase = it.animatedValue as Float; invalidate() }
    }

    init { importantForAccessibility = IMPORTANT_FOR_ACCESSIBILITY_NO } // The route rows carry the same information.

    fun set(route: Route, state: RouteState) { states[route.ordinal] = state; updateMotion(); invalidate() }

    private fun moving() = isAttachedToWindow && states.any { it == RouteState.TRYING } && ValueAnimator.areAnimatorsEnabled()
    private fun updateMotion() { if (moving()) { if (!spin.isStarted) spin.start() } else if (spin.isStarted) spin.cancel() }
    override fun onAttachedToWindow() { super.onAttachedToWindow(); updateMotion() }
    override fun onDetachedFromWindow() { spin.cancel(); super.onDetachedFromWindow() }

    override fun onMeasure(widthSpec: Int, heightSpec: Int) {
        val width = MeasureSpec.getSize(widthSpec)
        setMeasuredDimension(width, (width * 0.56f).roundToInt().coerceIn((190 * dp).roundToInt(), (260 * dp).roundToInt()))
    }

    override fun onSizeChanged(w: Int, h: Int, oldw: Int, oldh: Int) {
        glow = RadialGradient(w / 2f, h / 2f, 88 * dp, intArrayOf(0x599D72FF, 0x149D72FF, 0), floatArrayOf(0f, 0.45f, 1f), Shader.TileMode.CLAMP)
        val radius = 30 * dp
        val scale = radius * 2.5f / core.width
        corePaint.shader = BitmapShader(core, Shader.TileMode.CLAMP, Shader.TileMode.CLAMP).apply {
            setLocalMatrix(Matrix().apply { setScale(scale, scale); postTranslate(w / 2f - core.width * scale / 2, h / 2f - core.height * scale / 2) })
        }
    }

    private fun radiusX(i: Int) = (width / 2f - 24 * dp) * reach[i]
    private fun point(i: Int, degrees: Float): PointF {
        val rx = radiusX(i); val ry = rx * SQUASH
        val a = Math.toRadians(degrees.toDouble()); val t = Math.toRadians(tilt[i].toDouble())
        val x = rx * cos(a); val y = ry * sin(a)
        return PointF((width / 2f + x * cos(t) - y * sin(t)).toFloat(), (height / 2f + x * sin(t) + y * cos(t)).toFloat())
    }

    private fun orbit(canvas: Canvas, i: Int, sweep: Float) {
        val state = states[i]
        stroke.strokeWidth = 1.2f * dp
        stroke.pathEffect = if (state == RouteState.UNAVAILABLE) dash else null
        stroke.color = when (state) {
            RouteState.UNAVAILABLE -> Palette.alpha(Color.WHITE, 36)
            RouteState.IDLE -> Palette.alpha(Color.WHITE, 46)
            else -> Palette.alpha(Palette.of(state), 130)
        }
        val rx = radiusX(i); val ry = rx * SQUASH; val cx = width / 2f; val cy = height / 2f
        canvas.save(); canvas.rotate(tilt[i], cx, cy)
        canvas.drawArc(RectF(cx - rx, cy - ry, cx + rx, cy + ry), 0f, sweep, false, stroke)
        canvas.restore()
        stroke.pathEffect = null
    }

    override fun onDraw(canvas: Canvas) {
        val cx = width / 2f; val cy = height / 2f; val coreRadius = 30 * dp
        fill.shader = glow; canvas.drawCircle(cx, cy, 88 * dp, fill); fill.shader = null
        for (i in states.indices) orbit(canvas, i, 360f)
        for (i in states.indices) if (states[i] == RouteState.LIVE) {
            val p = point(i, anchor[i]); stroke.color = Palette.alpha(Palette.CYAN, 170); stroke.strokeWidth = 1.5f * dp
            canvas.drawLine(cx, cy, p.x, p.y, stroke)
        }
        canvas.drawCircle(cx, cy, coreRadius, corePaint)
        stroke.color = Palette.alpha(Color.WHITE, 60); stroke.strokeWidth = 1 * dp
        canvas.drawCircle(cx, cy, coreRadius, stroke)
        // Redraw the near half of each orbit so the rings pass in front of comma.
        for (i in states.indices) orbit(canvas, i, 180f)
        val animating = spin.isStarted
        for (i in states.indices) if (states[i] == RouteState.TRYING) {
            val head = anchor[i] + (if (animating) phase else 0.86f) * 360f
            for (k in 0 until 16) {
                val p = point(i, head - k * 3.2f)
                fill.color = Palette.alpha(Palette.VIOLET_SOFT, (235 * (1 - k / 16f)).roundToInt())
                canvas.drawCircle(p.x, p.y, (3.2f - k * 0.15f) * dp, fill)
            }
        }
        val nodeRadius = 19 * dp; val iconHalf = (9 * dp).roundToInt()
        for (i in states.indices) {
            val state = states[i]; val color = Palette.of(state); val p = point(i, anchor[i])
            fill.color = Palette.SPACE; canvas.drawCircle(p.x, p.y, nodeRadius, fill)
            fill.color = Palette.alpha(color, if (state == RouteState.UNAVAILABLE) 14 else 38); canvas.drawCircle(p.x, p.y, nodeRadius, fill)
            stroke.strokeWidth = 1.5f * dp; stroke.color = Palette.alpha(color, if (state == RouteState.UNAVAILABLE) 70 else 255)
            canvas.drawCircle(p.x, p.y, nodeRadius, stroke)
            if (state == RouteState.TRYING && animating) {
                stroke.color = Palette.alpha(color, ((1 - phase) * 150).roundToInt())
                canvas.drawCircle(p.x, p.y, nodeRadius + 12 * dp * phase, stroke)
            }
            icons[i].setTint(if (state == RouteState.UNAVAILABLE) Palette.alpha(Palette.MUTED, 150) else color)
            icons[i].setBounds(p.x.roundToInt() - iconHalf, p.y.roundToInt() - iconHalf, p.x.roundToInt() + iconHalf, p.y.roundToInt() + iconHalf)
            icons[i].draw(canvas)
        }
    }

    companion object { const val SQUASH = 0.36f }
}

/** The screen shown while not connected, and over the Galaxy page while it loads. */
class ConnectScreen(private val activity: Activity, private val onRoute: (Route) -> Unit, onRetry: () -> Unit,
                    onWifiSettings: () -> Unit, private val onAddress: (String) -> String?, onOptions: () -> Unit) {
    private val dp = activity.resources.displayMetrics.density
    private fun px(value: Number) = (value.toFloat() * dp).roundToInt()
    private val orbit = OrbitView(activity)
    private val headline = text(30f, Palette.ON, Palette.condensed).apply { setLineSpacing(0f, 0.95f) }
    private val detail = text(15f, Palette.MUTED).apply { setLineSpacing(px(3).toFloat(), 1f) }
    private val footer = text(13f, Palette.MUTED)
    private val states = mutableMapOf<Route, RouteState>()
    private val rows = mutableMapOf<Route, Row>()
    private val address = EditText(activity)
    private val addressRow = LinearLayout(activity)
    val view: ScrollView

    private inner class Row(val route: Route) {
        val icon = ImageView(activity).apply { setImageResource(route.icon); scaleType = ImageView.ScaleType.CENTER_INSIDE }
        val title = text(16f, Palette.ON, Palette.medium).apply { text = route.title }
        val state = text(14f, Palette.MUTED, Palette.condensed)
        val spinner = ProgressBar(activity).apply { isIndeterminate = true; indeterminateTintList = ColorStateList.valueOf(Palette.VIOLET_SOFT); visibility = View.GONE }
        val view = LinearLayout(activity).apply {
            orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL
            minimumHeight = px(68); setPadding(px(16), px(10), px(16), px(10))
            isClickable = true; isFocusable = true
            setOnClickListener { onRoute(route) }
            addView(icon, LinearLayout.LayoutParams(px(40), px(40)))
            addView(LinearLayout(activity).apply {
                orientation = LinearLayout.VERTICAL
                addView(title); addView(state)
            }, LinearLayout.LayoutParams(0, -2, 1f).apply { marginStart = px(14) })
            addView(spinner, LinearLayout.LayoutParams(px(20), px(20)))
        }
    }

    init {
        val panel = LinearLayout(activity).apply { orientation = LinearLayout.VERTICAL; setPadding(px(20), px(4), px(20), px(24)) }
        panel.addView(orbit, LinearLayout.LayoutParams(-1, -2))
        panel.addView(headline, LinearLayout.LayoutParams(-1, -2).apply { topMargin = px(8) })
        panel.addView(detail, LinearLayout.LayoutParams(-1, -2).apply { topMargin = px(8) })

        val list = LinearLayout(activity).apply {
            orientation = LinearLayout.VERTICAL
            background = GradientDrawable().apply { cornerRadius = px(24).toFloat(); setColor(Palette.SURFACE); setStroke(px(1), Palette.LINE) }
            clipToOutline = true
        }
        Route.entries.forEachIndexed { index, route ->
            if (index > 0) list.addView(View(activity).apply { setBackgroundColor(Palette.LINE) },
                LinearLayout.LayoutParams(-1, px(1)).apply { marginStart = px(70) })
            val row = Row(route); rows[route] = row; list.addView(row.view)
            route(route, RouteState.IDLE, "")
        }
        panel.addView(list, LinearLayout.LayoutParams(-1, -2).apply { topMargin = px(22) })

        panel.addView(text(16f, Palette.SPACE, Palette.medium).apply {
            text = "Try again"; gravity = Gravity.CENTER; isClickable = true; isFocusable = true
            background = RippleDrawable(ColorStateList.valueOf(0x40FFFFFF), GradientDrawable().apply { cornerRadius = px(26).toFloat(); setColor(Palette.VIOLET) }, null)
            setOnClickListener { onRetry() }
        }, LinearLayout.LayoutParams(-1, px(52)).apply { topMargin = px(20) })

        val links = LinearLayout(activity).apply { orientation = LinearLayout.HORIZONTAL }
        links.addView(link("Wi-Fi settings", onWifiSettings), LinearLayout.LayoutParams(0, -2, 1f))
        links.addView(link("Type an address") { toggleAddress() }, LinearLayout.LayoutParams(0, -2, 1f))
        links.addView(link("More options", onOptions), LinearLayout.LayoutParams(0, -2, 1f))
        panel.addView(links, LinearLayout.LayoutParams(-1, -2).apply { topMargin = px(6) })

        address.apply {
            hint = "192.168.1.10"; setSingleLine(); textSize = 16f
            setTextColor(Palette.ON); setHintTextColor(Palette.alpha(Palette.MUTED, 170))
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_URI
            imeOptions = EditorInfo.IME_ACTION_GO
            contentDescription = "comma address on your network"
            background = GradientDrawable().apply { cornerRadius = px(16).toFloat(); setColor(Palette.SURFACE); setStroke(px(1), Palette.LINE) }
            setPadding(px(16), px(12), px(16), px(12))
            setOnEditorActionListener { _, action, _ -> if (action == EditorInfo.IME_ACTION_GO) { open(); true } else false }
        }
        addressRow.apply {
            orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL; visibility = View.GONE
            addView(address, LinearLayout.LayoutParams(0, -2, 1f))
            addView(text(15f, Palette.SPACE, Palette.medium).apply {
                text = "Open"; gravity = Gravity.CENTER; isClickable = true; isFocusable = true; setPadding(px(20), 0, px(20), 0)
                background = RippleDrawable(ColorStateList.valueOf(0x40FFFFFF), GradientDrawable().apply { cornerRadius = px(16).toFloat(); setColor(Palette.VIOLET) }, null)
                setOnClickListener { open() }
            }, LinearLayout.LayoutParams(-2, px(48)).apply { marginStart = px(10) })
        }
        panel.addView(addressRow, LinearLayout.LayoutParams(-1, -2).apply { topMargin = px(8) })
        panel.addView(footer, LinearLayout.LayoutParams(-1, -2).apply { topMargin = px(18) })

        view = ScrollView(activity).apply {
            isFillViewport = true; setBackgroundColor(Palette.SPACE); clipToPadding = false
            addView(panel)
            setOnApplyWindowInsetsListener { v, insets ->
                v.setPadding(insets.systemWindowInsetLeft, insets.systemWindowInsetTop, insets.systemWindowInsetRight, insets.systemWindowInsetBottom); insets
            }
        }
    }

    private fun text(size: Float, color: Int, face: Typeface? = null) = TextView(activity).apply {
        textSize = size; setTextColor(color); face?.let { typeface = it }
    }

    private fun link(label: String, action: () -> Unit) = text(14f, Palette.VIOLET_SOFT, Palette.medium).apply {
        text = label; gravity = Gravity.CENTER; isClickable = true; isFocusable = true
        minHeight = px(48); setPadding(px(4), px(8), px(4), px(8))
        background = RippleDrawable(ColorStateList.valueOf(Palette.alpha(Palette.VIOLET, 60)), null, null)
        setOnClickListener { action() }
    }

    private fun toggleAddress() {
        val show = addressRow.visibility != View.VISIBLE
        addressRow.visibility = if (show) View.VISIBLE else View.GONE
        if (show) {
            address.requestFocus()
            activity.getSystemService(android.view.inputmethod.InputMethodManager::class.java)?.showSoftInput(address, 0)
            view.post { view.smoothScrollTo(0, addressRow.bottom) }
        }
    }

    private fun open() { onAddress(address.text.toString())?.let { address.error = it } }

    fun headline(text: String) { headline.text = text }
    fun detail(text: String) { detail.text = text }
    fun mode(transport: String?) {
        footer.text = when (transport) {
            "wifi" -> "Set to Wi-Fi and LAN only. Change this in More options."
            "bluetooth" -> "Set to Bluetooth only. Change this in More options."
            else -> "Automatic tries Galaxy Wi-Fi first, then your home network, then Bluetooth."
        }
    }
    fun route(route: Route, state: RouteState, text: String) {
        states[route] = state
        orbit.set(route, state)
        val row = rows[route] ?: return
        val color = Palette.of(state)
        row.state.text = text; row.state.setTextColor(color)
        row.state.visibility = if (text.isEmpty()) View.GONE else View.VISIBLE
        row.spinner.visibility = if (state == RouteState.TRYING) View.VISIBLE else View.GONE
        row.icon.imageTintList = ColorStateList.valueOf(if (state == RouteState.UNAVAILABLE) Palette.MUTED else color)
        row.icon.background = GradientDrawable().apply { shape = GradientDrawable.OVAL; setColor(Palette.alpha(color, if (state == RouteState.UNAVAILABLE) 16 else 34)) }
        row.title.setTextColor(if (state == RouteState.UNAVAILABLE) Palette.MUTED else Palette.ON)
        row.view.background = RippleDrawable(ColorStateList.valueOf(Palette.alpha(Palette.VIOLET, 60)),
            if (state == RouteState.TRYING) GradientDrawable().apply { setColor(Palette.alpha(Palette.VIOLET, 28)) } else null,
            GradientDrawable().apply { setColor(Color.WHITE) })
        row.view.contentDescription = if (text.isEmpty()) route.title else "${route.title}, $text"
    }
    fun state(route: Route) = states[route]
    fun busy() = states.values.any { it == RouteState.TRYING }

    /** Fade away to reveal the page underneath. */
    fun dismiss() {
        val remove = { (view.parent as? ViewGroup)?.removeView(view); Unit }
        if (ValueAnimator.areAnimatorsEnabled()) view.animate().alpha(0f).setDuration(240).withEndAction(remove).start() else remove()
    }

    companion object {
        /** Slim bar above live pages: which connection is in use, and a way to change it. */
        fun webBar(activity: Activity, route: Route, label: String, onConnections: () -> Unit): View {
            val dp = activity.resources.displayMetrics.density
            fun px(value: Number) = (value.toFloat() * dp).roundToInt()
            val bar = LinearLayout(activity).apply {
                orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL
                minimumHeight = px(48); setPadding(px(16), 0, px(4), 0)
                addView(ImageView(activity).apply { setImageResource(route.icon); imageTintList = ColorStateList.valueOf(Palette.CYAN) },
                    LinearLayout.LayoutParams(px(18), px(18)))
                addView(TextView(activity).apply {
                    text = label; textSize = 14f; setTextColor(Palette.ON); typeface = Palette.medium
                    setSingleLine(); ellipsize = TextUtils.TruncateAt.END
                }, LinearLayout.LayoutParams(0, -2, 1f).apply { marginStart = px(10) })
                addView(TextView(activity).apply {
                    text = "Connections"; textSize = 14f; setTextColor(Palette.VIOLET_SOFT); typeface = Palette.medium
                    gravity = Gravity.CENTER; minHeight = px(48); setPadding(px(12), 0, px(12), 0)
                    isClickable = true; isFocusable = true
                    background = RippleDrawable(ColorStateList.valueOf(Palette.alpha(Palette.VIOLET, 60)), null, null)
                    setOnClickListener { onConnections() }
                })
            }
            return LinearLayout(activity).apply {
                orientation = LinearLayout.VERTICAL; setBackgroundColor(Palette.SPACE)
                addView(bar, LinearLayout.LayoutParams(-1, -2))
                addView(View(activity).apply { setBackgroundColor(Palette.LINE) }, LinearLayout.LayoutParams(-1, px(1)))
                setOnApplyWindowInsetsListener { v, insets ->
                    v.setPadding(insets.systemWindowInsetLeft, insets.systemWindowInsetTop, insets.systemWindowInsetRight, 0); insets
                }
            }
        }
    }
}
