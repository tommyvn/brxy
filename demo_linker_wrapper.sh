#!/bin/bash

exec venv/bin/python -m pullproxy.linker $ROUTE venv/bin/python ./demo_fileserver.py
