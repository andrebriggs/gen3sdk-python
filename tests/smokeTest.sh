#!/bin/bash

#-- lib ------

# 
# Adapted from cloud-automation/gen3/lib/shunit.sh
#
because() {
  local exitCode
  if [[ $# -lt 2 ]]; then
    echo -e "\n\x1B[31mAssertion failed:\x1B[39m because takes 2 arguments: code message"
    exit 1
  fi
  let exitCode=$1
  let SHUNIT_ASSERT_COUNT+=1
  if [[ $exitCode != 0 ]]; then
    let SHUNIT_ASSERT_FAIL+=1
    echo -e "\n\x1B[31mAssertion failed:\x1B[39m $2"
    exit 1
  fi
  echo -e "\x1B[32mAssertion passed:\x1B[39m $2"
  return 0
}


run() {
    gen3 --auth qa-covid19 auth curl /user/user; because $? "auth curl /user/user works"
}


help() {
    cat - <<EOM
Run a series of non-destructive intractive tests against
the gen3sdk cli.

Use: bash smokeTest.sh run <auth flags>

Ex:
  bash smokeTest.sh --auth qa-covid19

EOM
}

#-- main ----

if [[ $# -lt 1 ]]; then
  help
  exit 0
fi

"$@"
