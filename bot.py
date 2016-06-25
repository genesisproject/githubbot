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

def push_message(data):
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
                        description=commit['message'],
                        branch=branch,
                        user=author['name'])

    return message

message_template_functions = {
    "push": push_message
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
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

@app.route('/gh-hook', methods=["POST"])
def gh_hook():
    event_type = request.headers.get('X-Github-Event')
    data = request.get_json()
    print('Got a webhook request for event type: %s' % event_type)

    # get a message to send to the Discord channel
    if event_type in message_template_functions:
        message = message_template_functions[event_type](data)
    else:
        print('Unhandled event of type %s' % event_type)
        return ''

    print(message)
    server = discord.utils.get(dc.servers, name=DISCORD_SERVER)
    channel = discord.utils.get(server.channels, name=DISCORD_CHANNEL)
    print("Sending message to channel %s on server %s" % (channel, server))

    asyncio.run_coroutine_threadsafe(dc.send_message(channel, message), dc.loop).result()

    return ''
