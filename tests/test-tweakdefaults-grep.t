  $ extpath=`dirname $TESTDIR`
  $ cp $extpath/tweakdefaults.py $TESTTMP # use $TESTTMP substitution in message
  $ cat >> $HGRCPATH << EOF
  > [extensions]
  > tweakdefaults=$TESTTMP/tweakdefaults.py
  > rebase=
  > EOF

Set up the repository with some simple files
  $ hg init repo
  $ cd repo
  $ mkdir grepdir
  $ cd grepdir
  $ echo 'foobarbaz' > grepfile1
  $ echo 'foobarboo' > grepfile2
  $ mkdir subdir1
  $ echo 'foobar_subdir' > subdir1/subfile1
  $ mkdir subdir2
  $ echo 'foobar_dirsub' > subdir2/subfile2
  $ hg add grepfile1
  $ hg add grepfile2
  $ hg add subdir1/subfile1
  $ hg add subdir2/subfile2
  $ hg commit -m "Added some files"
  $ echo 'foobarbazboo' > untracked1

Make sure grep finds patterns in tracked files, and excludes untracked files
  $ hg grep -n foobar
  grepfile1:1:foobarbaz
  grepfile2:1:foobarboo
  subdir1/subfile1:1:foobar_subdir
  subdir2/subfile2:1:foobar_dirsub
  $ hg grep -n barbaz
  grepfile1:1:foobarbaz
  $ hg grep -n barbaz .
  grepfile1:1:foobarbaz

Test searching in subdirectories, from the repository root
  $ hg grep -n foobar subdir1
  subdir1/subfile1:1:foobar_subdir
  $ hg grep -n foobar sub*
  subdir1/subfile1:1:foobar_subdir
  subdir2/subfile2:1:foobar_dirsub

Test searching in a sibling subdirectory, using a relative path
  $ cd subdir1
  $ hg grep -n foobar ../subdir2
  ../subdir2/subfile2:1:foobar_dirsub
  $ hg grep -n foobar
  subfile1:1:foobar_subdir
  $ hg grep -n foobar .
  subfile1:1:foobar_subdir
  $ cd ..

Test mercurial file patterns
  $ hg grep -n foobar 'glob:*rep*'
  grepfile1:1:foobarbaz
  grepfile2:1:foobarboo
