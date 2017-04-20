# brxy

It's a brokering proxy, a serverless in a box super double reverse gender changing proxy micro loadbalancer from the future

[![Build Status](https://travis-ci.org/tommyvn/brxy.png)](https://travis-ci.org/tommyvn/brxy)

## What is it?

brxy is a proxy that lets application instances choose how much traffic they want. A nice side effect of this is you can make any existing 12 factor web applicaion serverless with zero effort.

# How does it work?

brxy allows each instance of your applicaiton to choose how many concurrent connections it will serve. Rather then drowning your application brxy will hold new connections until your application is ready to serve them.

You can supply brxy with a command to run when it has to hold connections, when no backend is free to handle them, too.

An interesting side effect of these two features is that if you make that command a call out to a scheduler like Kubernetes, Mesos, Docker Swarm, etc, you get a massively scalable serverless architecture for your regular web applications with zero extra effort. It works with any language and any web framework (or TCP;)), no need to learn Lambda or Cloud Functions or a middleware that makes them work with your favourite framework.

# Serverless for the masses (of existing apps)

Here's the flow:

A request arrives on brxy for example.com
```
Interwebs =====> brxy
```

brxy has to hold the connection so it runs the startup command:
```
Interwebs =====> brxy
                  ⇩
          kubectl run example.com
```

Once the application is running a micro-proxy called linker collects the request and hands it to the example.com app
```
                                   somewhere in your kube
                                      cluster...
                            +--------------------------+
Interwebs =====> brxy <====== linker =====> example.com|
                            +--------------------------+

```

Well done, example.com is on hackernews. So long as the scheduler behind it is big enough you're all good...
```
                                               somewhere in your kube
                                                  cluster...
                            +---------+      +--------------------------+
Hacker News Interwebs =====>|         |<====== linker =====> example.com|+
Hacker News Interwebs =====>|         |      +--------------------------+|+
Hacker News Interwebs =====>|         |      +--------------------------++|
Hacker News Interwebs =====>|  brxy   |<====== linker =====> example.com|++
Hacker News Interwebs =====>|         |      +--------------------------+|+
Hacker News Interwebs =====>|         |      +--------------------------++|
Hacker News Interwebs =====>|         |<====== linker =====> example.com|++
                            +---------+      +--------------------------+|+
                                ⇩             +--------------------------+|
                  kubectl run example.com x 9  +--------------------------+

```

Tough crowd, traffic suddenly drops back to normal after an hour and a few seconds later you're back at 1 instance...
```
                                   somewhere in your kube
                                      cluster...
                            +--------------------------+
Interwebs =====> brxy <====== linker =====> example.com|
                            +--------------------------+

```

How do I run it?
----------------

### local demo

```
python3 -m brxy.edge -p 8080 -- ./demo_linker_wrapper.sh
curl localhost:8080
```

If you watch your process listing you'll see that it fires up a file server on your local directory on demand to serve requests. If you can reach 5 concurrent requests you'll see it fires up a second one to handle the extra load.
