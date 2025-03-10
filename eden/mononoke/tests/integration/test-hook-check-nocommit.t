# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This software may be used and distributed according to the terms of the
# GNU General Public License found in the LICENSE file in the root
# directory of this source tree.

# This tests @nocommit, so we need to suppress the lint
# @lint-ignore-every NOCOMMIT

  $ . "${TEST_FIXTURES}/library.sh"

  $ hook_test_setup check_nocommit <()

  $ hg up tip
  3 files updated, 0 files merged, 0 files removed, 0 files unresolved

No @nocommit, should work

  $ echo "foo" > foo
  $ hg ci -Aqm 1
  $ hgmn push -r . --to master_bookmark
  pushing rev 8b8214d70c17 to destination mononoke://$LOCALIP:$LOCAL_PORT/repo bookmark master_bookmark
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  updating bookmark master_bookmark

Has @nocommit, should fail

  $ hg up -q "min(all())"
  $ echo "bar @nocommit" > foo
  $ hg ci -Aqm 1
  $ hgmn push -r . --to master_bookmark
  pushing rev 2a4a4062249a to destination mononoke://$LOCALIP:$LOCAL_PORT/repo bookmark master_bookmark
  searching for changes
  remote: Command failed
  remote:   Error:
  remote:     hooks failed:
  remote:     check_nocommit for 2a4a4062249a2c8175ec17dc89a27ed30580ace2: File contains a @nocommit marker: foo
  remote: 
  remote:   Root cause:
  remote:     hooks failed:
  remote:     check_nocommit for 2a4a4062249a2c8175ec17dc89a27ed30580ace2: File contains a @nocommit marker: foo
  remote: 
  remote:   Debug context:
  remote:     "hooks failed:\ncheck_nocommit for 2a4a4062249a2c8175ec17dc89a27ed30580ace2: File contains a @nocommit marker: foo"
  abort: unexpected EOL, expected netstring digit
  [255]
