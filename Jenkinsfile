//@Library('gfxr-jenkins@main') _

library identifier: 'gfxr-utils@main', retriever: modernSCM(
  [$class: 'GitSCMSource',
   remote: 'https://github.com/ncesario-lunarg/jenkins-testing.git'])

pipeline {
    agent none
    stages {
        stage('Build') {
            parallel {
                stage ('Android Release') {
                    agent {
                        label "android-build"
                    }

                    steps {
                        script {
                            buildGFXR.cmd('git submodule update --init --recursive')

                            dir ('android') {
                                buildGFXR.cmd("./gradlew assembleRelease -Parm64-v8a")
                            }

                            stash includes: "android/layer/**/*,android/tools/**/*,android/test/**/*", name: buildGFXR.getStashName('android', 'release', '64')
                        }
                    }
                }
                
                stage ('Linux Debug') {
                    agent {
                        label "linux-build"
                    }

                    steps {
                        script {
                            buildGFXR.cmd('git submodule update --init --recursive')
                            buildGFXR.cmd('cmake -GNinja -Bbuild -DCMAKE_BUILD_TYPE=Debug')
                            buildGFXR.cmd('ninja -Cbuild')
                            stash includes: "build/layer/**/*,android/tools/**/*,android/scripts/**/*", name: buildGFXR.getStashName('linux', 'debug', '64')
                        }
                    }
                }

                stage ('Linux Release') {
                    agent {
                        label "linux-build"
                    }

                    steps {
                        script {
                            buildGFXR.cmd('git submodule update --init --recursive')
                            buildGFXR.cmd('cmake -GNinja -Bbuild -DCMAKE_BUILD_TYPE=Release')
                            buildGFXR.cmd('ninja -Cbuild')
                            stash includes: "build/layer/**/*,android/tools/**/*,android/scripts/**/*", name: buildGFXR.getStashName('linux', 'release', '64')
                        }
                    }
                }
            }
        }

        stage('Test') {
            parallel {
                stage('Pixel 6') {
                    agent {
                        label "android-test && android-pixel6"
                    }
                    steps {
                        buildGFXR('android', 'release', '64', 'pixel6')
                    }
                }

                stage('Emulator') {
                    agent {
                        label "android-test && android-emulator"
                    }
                    steps {
                        buildGFXR('android', 'release', '64', 'emulator')
                    }
                }
            }
        }
    }

    post {
        success {
            publishChecks()
        }
        failure {
            publishChecks()
        }
    }
}
