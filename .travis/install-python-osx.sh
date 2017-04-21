#!/bin/bash

if [[ $TRAVIS_OS_NAME == 'osx' ]]; then
    # brew update
    brew install pyenv || brew upgrade pyenv
    PYTHON_CONFIGURE_OPTS="--enable-framework" pyenv install 3.5.3
    eval "$(pyenv init -)"
    pyenv global 3.5.3
fi
