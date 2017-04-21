# edge

It's a brokering proxy, a serverless in a box super double reverse gender changing proxy micro loadbalancer from the future

[![Build Status](https://travis-ci.org/tommyvn/edge.png)](https://travis-ci.org/tommyvn/edge)

## What is it?

brxy is a proxy that lets application instances choose how much traffic they want. A nice side effect of this is you can make any existing 12 factor web application serverless with zero effort.

# How does it work?

brxy consists of two components, brxy.edge and brxy.node.

brxy.edge accepts connections and runs a supplied command if there isn't already a backend available to accept that connection.

brxy.node connects an application to brxy.edge and allows each instance of the application to choose how many concurrent connections it will serve. Rather then drowning an application brxy.edge will hold new connections until the application is ready to serve them.

An interesting side effect of these two features is that if the command supplied to brxy.node a call out to a scheduler like Kubernetes, Mesos, Docker Swarm, etc, you get a massively scalable serverless architecture for your regular web applications with zero extra development effort. It works with any language and any web framework (or TCP;)), no need to learn Lambda or Cloud Functions or a middleware that makes them (mostly) work with your favourite framework.

# Serverless for the masses (of existing apps)

Here's the flow:

A request arrives on edge for example.com
```
                 +-----------+
Interwebs =====> | brxy.edge |
                 +-----------+
```

edge has to hold the connection so it runs the startup command:
```
                 +-----------+
Interwebs =====> | brxy.edge |
                 +-----⇩-----+
               kubectl run example.com
```

Once the application is running a micro-proxy called  node  collects the request and hands it to the example.com app
```
                                           somewhere in your kube
                                              cluster...
                 +-----------+       +-------------------------------+
Interwebs =====> | brxy.edge | <======  brxy.node  =====> example.com|
                 +-----------+       +-------------------------------+

```

Well done, example.com is on hackernews. So long as the scheduler behind it is big enough you're all good...
```
                                                 somewhere in your kube
                                                    cluster...
                            +-----------+      +-------------------------------+
Hacker News Interwebs =====>|           |<======  brxy.node  =====> example.com|+
Hacker News Interwebs =====>|           |      +-------------------------------+|+
Hacker News Interwebs =====>|           |      +-------------------------------++|
Hacker News Interwebs =====>| brxy.edge |<======  brxy.node  =====> example.com|++
Hacker News Interwebs =====>|           |      +-------------------------------+|+
Hacker News Interwebs =====>|           |      +-------------------------------++|
Hacker News Interwebs =====>|           |<======  brxy.node  =====> example.com|++
                            +-----------+      +-------------------------------+|+
                                  ⇩             +-------------------------------+|
                    kubectl run example.com x 9  +-------------------------------+

```

Tough crowd, traffic suddenly drops back to normal after an hour and a few seconds later you're back at 1 instance...
```
                                         somewhere in your kube
                                            cluster...
                 +-----------+       +-------------------------------+
Interwebs =====> | brxy.edge | <======  brxy.node  =====> example.com|
                 +-----------+       +-------------------------------+

```

How do I run it?
----------------

### local demo

First, make sure you're using Python 3, this isn't 2008 after all. Alternatively you can grab binaries (yes golang fans, while admittedly not as nicely, Python can build binaries too) for Linux and osx over here: https://github.com/tommyvn/brxy/releases

```
python -m edge.edge -p 8080 -- python -m edge.node -- python demo.py
curl localhost:8080
```

If you watch your process listing you'll see that it fires up a file server on your local directory on demand to serve requests. If you can reach 5 concurrent requests you'll see it fires up a second one to handle the extra load. Reaching 5 concurrent requests isn't always as easy as it sounds but `demo.py` has your back. It's single threaded and `-d` introduces a delay into the response so the below will result in 4 copise spun up to magically make a single threaded blocking server a scalable serverless beast.

```
python -m edge.edge -p 8080 -- python -m edge.node -- python demo.py -d 10
curl localhost:8080 &
curl localhost:8080 &
curl localhost:8080 &
curl localhost:8080 &
```
