package link.firestar.companion

import android.app.job.JobParameters
import android.app.job.JobService
import android.os.Handler
import android.os.Looper
import java.util.concurrent.Executors
import java.util.concurrent.Future

class AppUpdateJob : JobService() {
    private val executor = Executors.newSingleThreadExecutor()
    private val handler = Handler(Looper.getMainLooper())
    private var active: JobParameters? = null
    private var task: Future<*>? = null

    override fun onStartJob(params: JobParameters): Boolean {
        active = params
        task = executor.submit {
            runCatching { AppUpdates.check(applicationContext) }
            handler.post { if (active === params) { active = null; jobFinished(params, false) } }
        }
        return true
    }

    override fun onStopJob(params: JobParameters): Boolean {
        active = null
        task?.cancel(true)
        return true
    }

    override fun onDestroy() {
        active = null
        executor.shutdownNow()
        handler.removeCallbacksAndMessages(null)
        super.onDestroy()
    }
}
