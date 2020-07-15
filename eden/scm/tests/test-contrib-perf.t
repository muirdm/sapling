#require py2
#chg-compatible

  $ disable treemanifest
#require test-repo

Set vars:

  $ . "$TESTDIR/helpers-testrepo.sh"
  $ CONTRIBDIR="$TESTDIR/../contrib"

Prepare repo:

  $ hg init

  $ echo this is file a > a
  $ hg add a
  $ hg commit -m first

  $ echo adding to file a >> a
  $ hg commit -m second

  $ echo adding more to file a >> a
  $ hg commit -m third

  $ hg up -r 0
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ echo merge-this >> a
  $ hg commit -m merge-able

  $ hg up -r 2
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved

perfstatus

  $ cat >> $HGRCPATH << EOF
  > [extensions]
  > perfstatusext=$CONTRIBDIR/perf.py
  > [perf]
  > presleep=0
  > stub=on
  > parentscount=1
  > EOF
  $ hg perfaddremove
  $ hg perfancestors
  $ hg perfancestorset 2
  $ hg perfannotate a
  $ hg perfbdiff -c 1
  $ hg perfbdiff --alldata 1
  $ hg perfbookmarks
  $ hg perfcca
  $ hg perfchangegroupchangelog
  $ hg perfchangeset 2
  $ hg perfctxfiles 2
  $ hg perfdiffwd
  $ hg perfdirfoldmap
  $ hg perfdirs
  $ hg perfdirstate
  $ hg perfdirstatedirs
  $ hg perfdirstatefoldmap
  $ hg perfdirstatewrite
  $ hg perffncacheencode
  $ hg perffncacheload
  $ hg perffncachewrite
  $ hg perfheads
  $ hg perfindex
  $ hg perflog
  $ hg perflookup 2
  $ hg perflrucache
  $ hg perfmanifest 2
  $ hg perfmergecalculate -r 3
  $ hg perfnodelookup 2
  $ hg perfpathcopies 1 2
  $ hg perfrawfiles 2
  $ hg perfrevlogindex -c
  $ hg perfrevlogrevisions .hg/store/data/a.i
  $ hg perfrevlogrevision -m 0
  $ hg perfrevlogchunks -c
  $ hg perfrevrange
  $ hg perfrevset 'all()'
  $ hg perfstartup
  $ hg perfstatus
  $ hg perftemplating
  $ hg perfwalk
  $ hg perfparents
