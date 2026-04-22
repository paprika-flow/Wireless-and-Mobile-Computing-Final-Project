package com.example.avatarfrontend

import android.content.Context
import android.graphics.Color
import android.net.wifi.WifiManager
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.widget.ImageView
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import fi.iki.elonen.NanoHTTPD
import java.io.IOException

class MainActivity : AppCompatActivity() {

    private lateinit var eyesImage: ImageView
    private lateinit var mouthImage: ImageView
    private lateinit var ipTextView: TextView
    private lateinit var statusTextView: TextView

    private lateinit var server: SimpleHttpServer

    // State tracker for connection status
    private var lastReceivedTime: Long = 0
    private val heartbeatHandler = Handler(Looper.getMainLooper())

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // Grab UI elements
        eyesImage = findViewById(R.id.eyesImage)
        mouthImage = findViewById(R.id.mouthImage)
        ipTextView = findViewById(R.id.ipTextView)
        statusTextView = findViewById(R.id.statusTextView)

        // Display the Wi-Fi IP address
        ipTextView.text = "IP: ${getLocalIpAddress()}:8080"

        // Start server
        server = SimpleHttpServer(8080)
        try {
            server.start(NanoHTTPD.SOCKET_READ_TIMEOUT, false)
        } catch (e: IOException) {
            e.printStackTrace()
            statusTextView.text = "SERVER ERROR"
            statusTextView.setTextColor(Color.RED)
        }

        // Start Heartbeat monitor to check if laptop is connected
        startHeartbeatMonitor()
    }

    override fun onDestroy() {
        super.onDestroy()
        server.stop()
        heartbeatHandler.removeCallbacksAndMessages(null)
    }

    // Fetches the phone's actual Wi-Fi IP Address
    private fun getLocalIpAddress(): String {
        val wifiManager = applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
        val ipAddress = wifiManager.connectionInfo.ipAddress
        return if (ipAddress == 0) {
            "Not on Wi-Fi"
        } else {
            String.format(
                "%d.%d.%d.%d",
                ipAddress and 0xff,
                ipAddress shr 8 and 0xff,
                ipAddress shr 16 and 0xff,
                ipAddress shr 24 and 0xff
            )
        }
    }

    // Checks every 500ms to see if we've heard from the laptop recently
    private fun startHeartbeatMonitor() {
        heartbeatHandler.post(object : Runnable {
            override fun run() {
                val timeSinceLastPing = System.currentTimeMillis() - lastReceivedTime
                if (lastReceivedTime == 0L || timeSinceLastPing > 2000) {
                    statusTextView.text = "Disconnected"
                    statusTextView.setTextColor(Color.parseColor("#FFBB33")) // Orange/Yellow
                } else {
                    statusTextView.text = "Connected \uD83D\uDFE2" // Text + Green circle emoji
                    statusTextView.setTextColor(Color.parseColor("#00FF00")) // Green
                }
                heartbeatHandler.postDelayed(this, 500) // Loop again in half a second
            }
        })
    }

    private fun updateAvatarState(eyeState: String, mouthState: String) {
        runOnUiThread {
            val eyeResId = when (eyeState) {
                "eyesClosed.PNG" -> R.drawable.eyes_closed
                "eyesWide.PNG" -> R.drawable.eyes_wide
                "eyesHappy.PNG" -> R.drawable.eyes_happy
                else -> R.drawable.eyes_neutral
            }

            val mouthResId = when (mouthState) {
                "mouthOpenSmile.PNG" -> R.drawable.mouth_open_smile
                "mouthOpen.PNG" -> R.drawable.mouth_open
                "mouthSmile.PNG" -> R.drawable.mouth_smile
                "MouthFrown.PNG" -> R.drawable.mouth_frown
                else -> R.drawable.mouth_neutral
            }

            eyesImage.setImageResource(eyeResId)
            mouthImage.setImageResource(mouthResId)
        }
    }

    inner class SimpleHttpServer(port: Int) : NanoHTTPD(port) {
        override fun serve(session: IHTTPSession): Response {
            // Update our heartbeat tracker the exact moment data arrives!
            lastReceivedTime = System.currentTimeMillis()

            val eye = session.parameters["eye"]?.firstOrNull() ?: "eyesNeutral.PNG"
            val mouth = session.parameters["mouth"]?.firstOrNull() ?: "mouthNeutral.PNG"

            updateAvatarState(eye, mouth)

            return newFixedLengthResponse("OK")
        }
    }
}