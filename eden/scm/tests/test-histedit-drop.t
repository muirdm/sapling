#chg-compatible
#debugruntest-compatible

  $ . "$TESTDIR/histedit-helpers.sh"

  $ enable histedit

  $ initrepo ()
  > {
  >     hg init r
  >     cd r
  >     for x in a b c d e f ; do
  >         echo $x > $x
  >         hg add $x
  >         hg ci -m $x
  >     done
  > }

  $ initrepo

log before edit
  $ hg log --graph
  @  commit:      652413bf663e
  │  user:        test
  │  date:        Thu Jan 01 00:00:00 1970 +0000
  │  summary:     f
  │
  o  commit:      e860deea161a
  │  user:        test
  │  date:        Thu Jan 01 00:00:00 1970 +0000
  │  summary:     e
  │
  o  commit:      055a42cdd887
  │  user:        test
  │  date:        Thu Jan 01 00:00:00 1970 +0000
  │  summary:     d
  │
  o  commit:      177f92b77385
  │  user:        test
  │  date:        Thu Jan 01 00:00:00 1970 +0000
  │  summary:     c
  │
  o  commit:      d2ae7f538514
  │  user:        test
  │  date:        Thu Jan 01 00:00:00 1970 +0000
  │  summary:     b
  │
  o  commit:      cb9a9f314b8b
     user:        test
     date:        Thu Jan 01 00:00:00 1970 +0000
     summary:     a
  

edit the history
  $ hg histedit 177f92b77385 --commands - 2>&1 << EOF | fixbundle
  > drop 177f92b77385 c
  > pick e860deea161a e
  > pick 652413bf663e f
  > pick 055a42cdd887 d
  > EOF

log after edit
  $ hg log --graph
  @  commit:      f518305ce889
  │  user:        test
  │  date:        Thu Jan 01 00:00:00 1970 +0000
  │  summary:     d
  │
  o  commit:      a4f7421b80f7
  │  user:        test
  │  date:        Thu Jan 01 00:00:00 1970 +0000
  │  summary:     f
  │
  o  commit:      ee283cb5f2d5
  │  user:        test
  │  date:        Thu Jan 01 00:00:00 1970 +0000
  │  summary:     e
  │
  o  commit:      d2ae7f538514
  │  user:        test
  │  date:        Thu Jan 01 00:00:00 1970 +0000
  │  summary:     b
  │
  o  commit:      cb9a9f314b8b
     user:        test
     date:        Thu Jan 01 00:00:00 1970 +0000
     summary:     a
  

Check histedit_source

  $ hg log --debug --rev f518305ce889
  commit:      f518305ce889c07cb5bd05522176d75590ef3324
  phase:       draft
  manifest:    d3d4f51c157ff242c32ff745d4799aaa26ccda44
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  files+:      d
  extra:       branch=default
  extra:       histedit_source=055a42cdd88768532f9cf79daa407fc8d138de9b
  description:
  d
  
  

manifest after edit
  $ hg manifest
  a
  b
  d
  e
  f

Drop the last changeset

  $ hg histedit ee283cb5f2d5 --commands - 2>&1 << EOF | fixbundle
  > pick ee283cb5f2d5 e
  > pick a4f7421b80f7 f
  > drop f518305ce889 d
  > EOF
  $ hg log --graph
  @  commit:      a4f7421b80f7
  │  user:        test
  │  date:        Thu Jan 01 00:00:00 1970 +0000
  │  summary:     f
  │
  o  commit:      ee283cb5f2d5
  │  user:        test
  │  date:        Thu Jan 01 00:00:00 1970 +0000
  │  summary:     e
  │
  o  commit:      d2ae7f538514
  │  user:        test
  │  date:        Thu Jan 01 00:00:00 1970 +0000
  │  summary:     b
  │
  o  commit:      cb9a9f314b8b
     user:        test
     date:        Thu Jan 01 00:00:00 1970 +0000
     summary:     a
  

  $ hg histedit cb9a9f314b8b --commands - 2>&1 << EOF | fixbundle
  > pick cb9a9f314b8b a
  > pick ee283cb5f2d5 e
  > EOF
  hg: parse error: missing rules for changeset a4f7421b80f7
  (use "drop a4f7421b80f7" to discard, see also: 'hg help -e histedit.config')
  $ hg --config histedit.dropmissing=True histedit  cb9a9f314b8b --commands - 2>&1 << EOF | fixbundle
  > EOF
  hg: parse error: no rules provided
  (use strip extension to remove commits)
  $ hg --config histedit.dropmissing=True histedit  cb9a9f314b8b --commands - 2>&1 << EOF | fixbundle
  > pick cb9a9f314b8b a
  > pick ee283cb5f2d5 e
  > EOF
  $ hg log --graph
  @  commit:      e99c679bf03e
  │  user:        test
  │  date:        Thu Jan 01 00:00:00 1970 +0000
  │  summary:     e
  │
  o  commit:      cb9a9f314b8b
     user:        test
     date:        Thu Jan 01 00:00:00 1970 +0000
     summary:     a
  
