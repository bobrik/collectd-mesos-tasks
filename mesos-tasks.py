#! /usr/bin/env python

import collectd
import json
import urllib2

CONFIGS = []

METRICS = [
    "cpus_limit",
    "cpus_system_time_secs",
    "cpus_user_time_secs",
    "mem_limit_bytes",
    "mem_rss_bytes"
]

def configure_callback(conf):
    """Receive configuration"""

    host = "127.0.0.1"
    port = 5051

    for node in conf.children:
        if node.key == "Host":
            host = node.values[0]
        elif node.key == "Port":
            port = int(node.values[0])
        else:
            collectd.warning("mesos-tasks plugin: Unknown config key: %s." % node.key)

    CONFIGS.append({
        "host": host,
        "port": port,
    })

def fetch_json(url):
    """Fetch json from url"""
    try:
        return json.load(urllib2.urlopen(url, timeout=5))
    except urllib2.URLError, e:
        collectd.error("mesos-tasks plugin: Error connecting to %s - %r" % (url, e))
        return None

def fetch_metrics(conf):
    """Fetch metrics from slave"""
    return fetch_json("http://%s:%d/monitor/statistics.json" % (conf["host"], conf["port"]))

def fetch_state(conf):
    """Fetch state from slave"""
    return fetch_json("http://%s:%d/state.json" % (conf["host"], conf["port"]))

def read_stats(conf):
    """Read stats from specified slave"""

    metrics = fetch_metrics(conf)
    state = fetch_state(conf)

    if metrics is None or state is None:
        return

    tasks = {}

    for framework in state["frameworks"]:
        for executor in framework["executors"]:
            for task in executor["tasks"]:
                info = {}

                labels = {}
                if "labels" in task:
                    for label in task["labels"]:
                        labels[label["key"]] = label["value"]

                info["labels"] = labels

                tasks[task["id"]] = info

    for task in metrics:
        if task["source"] not in tasks:
            collectd.warning("mesos-tasks plugin: Task %s found in metrics, but missing in state" % task["source"])
            continue

        info = tasks[task["source"]]
        if "collectd_app" not in info["labels"]:
            continue

        app = info["labels"]["collectd_app"].replace(".", "_")
        instance = task["source"].replace(".", "_")

        for metric in METRICS:
            if metric not in task["statistics"]:
                continue

            val = collectd.Values(plugin="mesos-tasks")
            val.type = "gauge"
            val.plugin_instance = app + "." + instance
            val.type_instance = metric
            val.values = [task["statistics"][metric]]
            val.dispatch()

def read_callback():
    """Read stats from configured slaves"""
    for conf in CONFIGS:
        read_stats(conf)

collectd.register_config(configure_callback)
collectd.register_read(read_callback)
