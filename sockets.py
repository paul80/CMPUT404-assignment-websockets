#!/usr/bin/env python
# coding: utf-8
# Copyright (c) 2013-2014 Abram Hindle
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# CMPUT 410 Winter 2015 Assignment Submission
# Due: March 18. 2015
# Original assignment creator: Abram Hindle
# Assignment Contributors: Paul Nhan (pnhan), Jessica Surya (jsurya)
#
# References: Web Socket example code 
#   https://github.com/abramhindle/WebSocketsExamples
#

import flask
from flask import Flask, request, make_response
from flask_sockets import Sockets
import gevent
from gevent import queue
import time
import json
import os

app = Flask(__name__)
sockets = Sockets(app)
app.debug = True

clients = list()
def send_all(msg):
    for client in clients:
        client.put( msg )

def send_all_json(obj):
    send_all( json.dumps(obj) )

class Client:
    def __init__(self):
        self.queue = queue.Queue()
    def put(self, v):
        self.queue.put_nowait(v)
    def get(self):
        return self.queue.get()


class World:
    def __init__(self):
        self.clear()
        # we've got listeners now!
        self.listeners = list()
        
    def add_set_listener(self, listener):
        self.listeners.append( listener )

    def update(self, entity, key, value):
        entry = self.space.get(entity,dict())
        entry[key] = value
        self.space[entity] = entry
        self.update_listeners(entity)

    def set(self, entity, data):
        self.space[entity] = data
        self.update_listeners( entity )

    def update_listeners(self, entity):
        '''update the set listeners'''
        for listener in self.listeners:
            try:
                listener(entity, self.get(entity))
            except:
                self.listeners.remove(listener)

    def clear(self):
        self.space = dict()

    def get(self, entity):
        return self.space.get(entity,dict())
    
    def world(self):
        return self.space

myWorld = World()        

def set_listener( ws, entity, data ):
    ''' do something with the update ! '''
    ent = {};
    ent[entity] = data
    ws.send(json.dumps(ent))
        
@app.route('/')
def hello():
    '''Return something coherent here.. perhaps redirect to /static/index.html '''
    return flask.redirect("/static/index.html")


# def read_ws(ws,client):
#     '''A greenlet function that reads from the websocket and updates the world'''
#     msg = ws.receive()
#     print "WS RECV: %s" % msg
#     packet = json.loads(msg)
#     for ent in packet:
#         for key in packet[ent]:
#             myWorld.update(ent, key, packet[ent][key])
#         myWorld.update_listeners(ent)

def read_ws(ws,client):
    #some greenlit stuff ...
    try:
        while True:
            msg=ws.receive()
            print "WS RECV: %s" % msg
            if (msg is not None):
                packet= json.loads(msg)
                send_all_json(packet)

                #From old part
                for ent in packet:
                    for key in packet[ent]:
                        myWorld.update(ent, key, packet[ent][key])
                myWorld.update_listeners(ent)
            else:
                break
    except:
        '''Done'''


@sockets.route('/subscribe')
def subscribe_socket(ws):
    '''Fulfill ...'''
    client= Client()
    clients.append(client)
    g= gevent.spawn(read_ws,ws,client)
    try:
        while True:
            msg=client.get()
            ws.send(msg)
    except Exception as e:
        print "WS error %s" % e
    finally:
        clients.remove(client)
        gevent.kill(g)
# def subscribe_socket(ws):
#     '''Fufill the websocket URL of /subscribe, every update notify the
#        websocket and read updates from the websocket '''
   
#    #add_set_listener
#     myWorld.add_set_listener(ws)

#     ws.send(json.dumps(myWorld.world()))
#     print "Subscribing"
#     while True:
#         try:
#             read_ws(ws,None)
#         except:
#             ws.close()
#             myWorld.listeners.remove(ws)
#             break

def flask_post_json():
    '''Ah the joys of frameworks! They do so much work for you
       that they get in the way of sane operation!'''
    if (request.json != None):
        return request.json
    elif (request.data != None and request.data != ''):
        return json.loads(request.data)
    else:
        return json.loads(request.form.keys()[0])

@app.route("/entity/<entity>", methods=['POST','PUT'])
def update(entity):
    '''update the entities via this interface'''
    # Get the json 
    obj = flask_post_json()
    
    # call myWorld.update on the entity, key, value
    for key in obj:
        print "key = " + str(key)
        myWorld.update(entity, key, obj[key])

    # Return the updated entity
    return obj

@app.route("/world", methods=['POST','GET'])    
def world():
    '''you should probably return the world here'''
    resp = make_response(json.dumps(myWorld.world()))
    resp.headers['Content-Type'] = "application/json"
    return resp

@app.route("/entity/<entity>")    
def get_entity(entity):
    '''This is the GET version of the entity interface, return a representation of the entity'''
    return json.dumps(myWorld.get(entity))

@app.route("/clear", methods=['POST','GET'])
def clear():
    '''Clear the world out!'''
    myWorld.clear()
    return ""



if __name__ == "__main__":
    ''' This doesn't work well anymore:
        pip install gunicorn
        and run
        gunicorn -k flask_sockets.worker sockets:app
    '''
    app.run()
