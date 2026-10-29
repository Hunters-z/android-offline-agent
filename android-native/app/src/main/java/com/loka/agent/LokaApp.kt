package com.loka.agent

import android.app.Application

class LokaApp : Application() {
    override fun onCreate() {
        super.onCreate()
        Repos.init(this)
    }
}
