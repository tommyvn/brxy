# pullproxy

Super double reverse proxy micro loadbalancer from the future

[![Build Status](https://travis-ci.org/drie/pullproxy.png)](https://travis-ci.org/drie/pullproxy)

## What is it?

pullproxy is a loadbalancer that addresses an issue that exists in all modern loadbalancers. All modern loadbalancers decide how much load an application can handle when really it's the application that should make that decision.

# How does it work?

pullproxy allows each instance of your applicaiton to choose how many concurrent connections it will serve. Rather then drowning your application pullproxy will hold new connections until your application is ready to serve them.

You can supply pullproxy with a command to run when it has to hold connections too.

An interesting side effect of these two features is that if you make that command a call out to a scheduler like Kubernetes, Mesos, Docker Swarm, etc, you get a massively scalable serverless architecture for your regular web applications with no more work needed. It works with any language and any web framework (or TCP;)), no need to learn Lambda or Cloud Functions. Wait, serverless, what?

# Serverless

Here's the flow:

A request arrives on pullproxy for example.com
```
Interwebs =====> pullproxy
```

pullproxy has to hold the connection so it runs the startup command:
```
Interwebs =====> pullproxy
                    ⇩
            kubectl run example.com
```

Once the application is running a micro-proxy called linker collects the request and hands it to the example.com app
```
                                   somewhere in your kube
                                      cluster...
                                 +--------------------------+
Interwebs =====> pullproxy <====== linker =====> example.com|
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
Hacker News Interwebs =====>|pullproxy|<====== linker =====> example.com|++
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
Interwebs =====> pullproxy <====== linker =====> example.com|
                                 +--------------------------+

```
