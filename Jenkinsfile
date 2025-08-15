////////////////////////////////////////////////////////////////////////////////
// Start of Groovy code that could go into a private repo and be specified in
// Jenkins as a "library."

def gitCheckout(String url, String branch) {
   checkout scmGit(
      branches: [[name: branch]],
      userRemoteConfigs: [[url: url]],
      extensions: [
            cloneOption(noTags: true),
            cloneOption(shallow: true),
			submodule(depth: 1, recursiveSubmodules: true)
      ]
   )
}

def getStashName(String platform, String type, String bits) {
  return "${platform}-build-${type}-${bits}-artifacts"
}

def cmd(String cmdStr) {
	if (isUnix()) {
		sh cmdStr
	} else {
		powershell cmdStr
	}
}

final GFXR_REPO = "git@github.com:LunarG/gfxreconstruct.git"
final SUITES_REPO = "git@github.com:LunarG/ci-gfxr-suites.git"
final TESTS_REPO = "git@github.com:LunarG/VulkanTests.git"

def buildGFXR(String platform, String type, String bits, String args = '') {
   // The fetch/checkout lets it work with Gerrit
   cmd 'submodule update --init --recursive'
   cmd 'git describe --tags --always'

   gitCheckout(SUITES_REPO, 'master')
   gitCheckout(TESTS_REPO, 'master')

   //cmd "python3 VulkanTests/gfxrecontest.py --build-mode ${type} --bits ${bits} ${args} --suite \"ci-gfxr-suites/${GFXRECON_TRACE_SUBDIR}/${TEST_SUITE}\" --trace-dir \"${GFXRECON_TRACE_DIR}\""
   cmd "python3 VulkanTests/gfxrecontest.py --build-mode ${type} --bits ${bits} ${args}"

   // TODO: only stash necessary binaries, not the entire build directory
   stash includes: "build/layer/**/*", "build/tools/**/*", name: getStashName(platform, type, bits)
}

def testGFXR(String platform, String type, String bits) {
   gitCheckout(TESTS_REPO, 'master')
   unstash name: getStashName(platform, type, bits)

   cmd "python3 VulkanTests/gfxrecontest.py --build-mode ${type} --bits ${bits} ${args} --suite \"ci-gfxr-suites/${GFXRECON_TRACE_SUBDIR}/${TEST_SUITE}\" --trace-dir \"${GFXRECON_TRACE_DIR}\""
}

def buildAndTest(String platform, String type, String bits, String labelCondition = '') {
	if (labelCondition != '') {
		labelCondition = "${platform} && ${labelCondition}"
	} else {
		labelCondition = platform
	}
	return {
		stage("${platform} ${bits} bit (${type})") {
			stages {
				stage('build') {
					agent {
						label "${labelCondition} && gfxr-${platform}-build"
					}
					steps {
						buildGFXR(platform, type, bits)
					}
				}

				stage('test') {
					agent {
						label "${labelCondition} && gfxr-${platform}-test"
					}

					steps {
						testGFXR(platform, type, bits)
					}
				}
			}
		}
	}
}

// End of "private" groovy code
////////////////////////////////////////////////////////////////////////////////

////////////////////////////////////////////////////////////////////////////////
// Start of public code

pipeline {
   agent none
   stages {
      stage('Build Pipelines') {
         publishChecks()
		 parallel {
		 	buildAndTest('linux', 'release', '64', 'mesa')
		 	buildAndTest('linux', 'release', '64', 'nvidia')
		 	buildAndTest('linux', 'debug', '32', 'mesa')
		 	buildAndTest('linux', 'debug', '32', 'nvidia')

			buildAndTest('windows', 'release', '64', 'nvidia')
			buildAndTest('windows', 'release', '64', 'amd')
			buildAndTest('windows', 'debug', '32', 'nvidia')
			buildAndTest('windows', 'debug', '32', 'amd')

			buildAndTest('android', 'release', '64')
			buildAndTest('android', 'debug', '64')

			buildAndTest('macos', 'release', '64')
			buildAndTest('macos', 'debug', '64')
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

// End of public code
////////////////////////////////////////////////////////////////////////////////
