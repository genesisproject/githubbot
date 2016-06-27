#!/usr/bin/env python3
"""
A bot for pushing Github updates to a Discord channel

Author: Erin <sylphofelectricity@gmail.com>
"""

import os
import asyncio
import threading
import functools
from flask import Flask, request
import discord
import requests

DISCORD_SERVER = os.environ["DISCORD_SERVER"]
DISCORD_CHANNEL = os.environ["DISCORD_CHANNEL"]
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]

def shorten_url(url):
    r = requests.post('https://git.io', data={'url': url})
    return r.headers['Location']

def gh_push_message(data):
    repo = data['repository']['full_name']
    commits = data['commits']
    branch = data['ref'].split('/')[-1]

    message = "[**{repo}**][*{branch}*] {n_commits} new {commit}:".format(repo=repo,
                        n_commits=len(commits), branch=branch,
                        commit="commits" if len(commits) > 1 else "commit")
    for commit in commits:
        author = commit['author']
        shorturl = shorten_url(commit['url'])
        message += "\n{url}: {hash} ↪ {description} ↬ {branch} ↯ {user}".format(url=shorturl,
                        hash=commit['id'][0:7],
                        description=commit['message'].splitlines()[0],
                        branch=branch,
                        user=author['name'])

    return message

github_message_template_functions = {
    "push": gh_push_message
}

app = Flask(__name__)
dc = discord.Client()
loop = asyncio.new_event_loop()
def start_discord_client():
    asyncio.set_event_loop(loop)
    print("Starting Discord client")
    dc.run(DISCORD_TOKEN)
t = threading.Thread(target=start_discord_client)
t.start()

@dc.event
@asyncio.coroutine
def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

@app.route('/gh-hook', methods=["POST"])
def gh_hook():
    event_type = request.headers.get('X-Github-Event')
    data = request.get_json()
    print('Github hook route called.')
    print('Got a webhook request for event type: %s' % event_type)

    # get a message to send to the Discord channel
    if event_type in github_message_template_functions:
        message = github_message_template_functions[event_type](data)
    else:
        print('Unhandled event of type %s' % event_type)
        return ''

    print(message)
    server = discord.utils.get(dc.servers, name=DISCORD_SERVER)
    channel = discord.utils.get(server.channels, name=DISCORD_CHANNEL)
    print("Sending message to channel %s on server %s" % (channel, server))

    asyncio.run_coroutine_threadsafe(dc.send_message(channel, message), dc.loop).result()

    return ''


def ucb_build_status(status, data):
    project = data['projectName']
    build_target = data['build_target']
    build_number = data['buildNumber']

    status_emoji = {'succeeded': '☑', 'failed': '☒', 'cancelled': '©'}

    return "{statemoji} [**{project}**] Build #{build_n} (target:{target}) {status}".format(stateemoji=status_emoji,
                            project=project, build_n=build_number, target=build_target, stat=status)

ucb_message_template_functions = {
    'ProjectBuildSuccess': functools.partial(ucb_build_status, 'succeeded'),
    'ProjectBuildFailure': functools.partial(ucb_build_status, 'failed'),
    'ProjectBuildCanceled': functools.partial(ucb_build_status, 'canceled')
}

@app.route('/ucb-hook', methods=["POST"])
def ucb_hook():
    event_type = request.headers.get('X-UnityCloudBuild-Event')
    data = request.get_json()
    print('Unity Cloud Build hook route called')
    print('Got a webhook request for event type: %s' % event_type)

    # get a message to send to the Discord channel
    if event_type in ucb_message_template_functions:
        message = ucb_message_template_functions[event_type](data)
    else:
        print('Unhandled event of type %s' % event_type)
        return ''

    print(message)
    server = discord.utils.get(dc.servers, name=DISCORD_SERVER)
    channel = discord.utils.get(server.channels, name=DISCORD_CHANNEL)
    print("Sending message to channel %s on server %s" % (channel, server))

    asyncio.run_coroutine_threadsafe(dc.send_message(channel, message), dc.loop).result()

    return ''
