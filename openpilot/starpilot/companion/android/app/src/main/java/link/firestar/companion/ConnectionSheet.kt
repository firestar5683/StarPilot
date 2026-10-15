package link.firestar.companion

import android.app.Activity
import android.app.Dialog
import android.content.res.ColorStateList
import android.graphics.Color
import android.graphics.drawable.ColorDrawable
import android.graphics.drawable.GradientDrawable
import android.graphics.drawable.RippleDrawable
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.view.Window
import android.widget.*
import kotlin.math.roundToInt

/** How the app reaches comma, as stored in the "transport" preference. */
enum class Transport(val key: String, val title: String, val icon: Int, val summary: String) {
    AUTO("auto", "Automatic", R.drawable.ic_route_auto, "Tries Galaxy Wi-Fi, then your home network, then Bluetooth."),
    WIFI("wifi", "Wi-Fi & LAN", R.drawable.ic_route_wifi, "Galaxy Wi-Fi or your home network. Never Bluetooth."),
    BLUETOOTH("bluetooth", "Bluetooth", R.drawable.ic_route_bluetooth, "Bluetooth only, for when there's no Wi-Fi in reach.");
    companion object { fun of(key: String?) = entries.firstOrNull { it.key == key } ?: AUTO }
}

/** Galaxy-styled bottom sheet with every connection choice, replacing the stock list dialog. */
class ConnectionSheet(private val activity: Activity, current: Transport) {
    private val dp = activity.resources.displayMetrics.density
    private fun px(value: Number) = (value.toFloat() * dp).roundToInt()
    private val dialog = Dialog(activity)
    private val content = LinearLayout(activity).apply { orientation = LinearLayout.VERTICAL; setPadding(px(20), px(22), px(20), px(20)) }
    private val tiles = mutableMapOf<Transport, LinearLayout>()
    private val summary = text(13f, Palette.MUTED)
    private var selected = current

    init {
        content.addView(text(22f, Palette.ON, Palette.condensed).apply { text = "Connections" })
        content.addView(LinearLayout(activity).apply {
            orientation = LinearLayout.HORIZONTAL
            Transport.entries.forEachIndexed { index, transport ->
                val tile = tile(transport); tiles[transport] = tile
                addView(tile, LinearLayout.LayoutParams(0, px(84), 1f).apply { if (index > 0) marginStart = px(8) })
            }
        }, LinearLayout.LayoutParams(-1, -2).apply { topMargin = px(16) })
        content.addView(summary, LinearLayout.LayoutParams(-1, -2).apply { topMargin = px(10) })
        paint()
        dialog.requestWindowFeature(Window.FEATURE_NO_TITLE)
        dialog.setContentView(ScrollView(activity).apply {
            addView(content)
            background = GradientDrawable().apply {
                val r = px(28).toFloat(); cornerRadii = floatArrayOf(r, r, r, r, 0f, 0f, 0f, 0f)
                setColor(Palette.SURFACE); setStroke(px(1), Palette.LINE)
            }
        })
        dialog.window?.apply {
            setBackgroundDrawable(ColorDrawable(Color.TRANSPARENT))
            setLayout(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
            setGravity(Gravity.BOTTOM)
            setWindowAnimations(android.R.style.Animation_InputMethod)
        }
    }

    /** Called with the new mode after the selection has had a moment on screen. */
    fun onTransport(choose: (Transport) -> Unit) = apply {
        tiles.forEach { (transport, tile) ->
            tile.setOnClickListener {
                selected = transport; paint()
                tile.postDelayed({ dismiss(); choose(transport) }, 180)
            }
        }
    }

    fun group(title: String, build: Group.() -> Unit) = apply {
        content.addView(text(14f, Palette.VIOLET_SOFT, Palette.medium).apply { text = title },
            LinearLayout.LayoutParams(-1, -2).apply { topMargin = px(24); marginStart = px(4) })
        val list = LinearLayout(activity).apply {
            orientation = LinearLayout.VERTICAL; clipToOutline = true
            background = GradientDrawable().apply { cornerRadius = px(18).toFloat(); setColor(Palette.SPACE); setStroke(px(1), Palette.LINE) }
        }
        Group(list).build()
        content.addView(list, LinearLayout.LayoutParams(-1, -2).apply { topMargin = px(8) })
    }

    inner class Group(private val list: LinearLayout) {
        fun action(title: String, detail: String? = null, danger: Boolean = false, run: () -> Unit) {
            if (list.childCount > 0) list.addView(View(activity).apply { setBackgroundColor(Palette.LINE) },
                LinearLayout.LayoutParams(-1, px(1)).apply { marginStart = px(16) })
            list.addView(LinearLayout(activity).apply {
                orientation = LinearLayout.VERTICAL; gravity = Gravity.CENTER_VERTICAL
                minimumHeight = px(56); setPadding(px(16), px(10), px(16), px(10))
                isClickable = true; isFocusable = true
                background = RippleDrawable(ColorStateList.valueOf(Palette.alpha(if (danger) Palette.ERROR else Palette.VIOLET, 60)), null, GradientDrawable().apply { setColor(Color.WHITE) })
                addView(text(16f, if (danger) Palette.ERROR else Palette.ON, Palette.medium).apply { text = title })
                if (detail != null) addView(text(13f, Palette.MUTED).apply { text = detail }, LinearLayout.LayoutParams(-1, -2).apply { topMargin = px(2) })
                contentDescription = if (detail == null) title else "$title. $detail"
                setOnClickListener { dismiss(); run() }
            }, LinearLayout.LayoutParams(-1, -2))
        }
    }

    fun show() { if (!activity.isFinishing && !activity.isDestroyed) dialog.show() }
    private fun dismiss() { if (dialog.isShowing) dialog.dismiss() }

    private fun tile(transport: Transport) = LinearLayout(activity).apply {
        orientation = LinearLayout.VERTICAL; gravity = Gravity.CENTER
        isClickable = true; isFocusable = true
        addView(ImageView(activity).apply { setImageResource(transport.icon) }, LinearLayout.LayoutParams(px(24), px(24)))
        addView(text(14f, Palette.ON, Palette.medium).apply { text = transport.title; gravity = Gravity.CENTER; maxLines = 1 },
            LinearLayout.LayoutParams(-2, -2).apply { topMargin = px(8) })
    }

    private fun paint() {
        tiles.forEach { (transport, tile) ->
            val on = transport == selected
            val color = if (on) Palette.VIOLET_SOFT else Palette.MUTED
            (tile.getChildAt(0) as ImageView).imageTintList = ColorStateList.valueOf(color)
            (tile.getChildAt(1) as TextView).setTextColor(if (on) Palette.ON else Palette.MUTED)
            tile.isSelected = on
            tile.contentDescription = if (on) "${transport.title}, selected" else transport.title
            tile.background = RippleDrawable(ColorStateList.valueOf(Palette.alpha(Palette.VIOLET, 60)), GradientDrawable().apply {
                cornerRadius = px(18).toFloat()
                setColor(if (on) Palette.alpha(Palette.VIOLET, 40) else Palette.SPACE)
                setStroke(px(if (on) 1.5f else 1f), if (on) Palette.VIOLET else Palette.LINE)
            }, null)
        }
        summary.text = selected.summary
    }

    private fun text(size: Float, color: Int, face: android.graphics.Typeface? = null) = TextView(activity).apply {
        textSize = size; setTextColor(color); face?.let { typeface = it }
    }
}
