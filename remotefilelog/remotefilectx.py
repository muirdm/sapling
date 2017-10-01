# remotefilectx.py - filectx/workingfilectx implementations for remotefilelog
#
# Copyright 2013 Facebook, Inc.
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2 or any later version.

import collections
from mercurial.i18n import _
from mercurial.node import bin, hex, nullid, nullrev
from mercurial import context, util, error, ancestor, phases, extensions

propertycache = util.propertycache
conduit = None
FASTLOG_TIMEOUT_IN_SECS = 0.5

def createconduit(ui):
    try:
        conduit = extensions.find("fbconduit")
    except KeyError:
        try:
            from hgext3rd import fbconduit as conduit
        except ImportError:
            ui.log('linkrevfixup',
                   _('unable to find fbconduit extension\n'))
            return False
    if not util.safehasattr(conduit, 'conduit_config'):
        ui.log('linkrevfixup',
               _('incompatible conduit module; disabling fastlog\n'))
        return False
    if not conduit.conduit_config(ui):
        ui.log('linkrevfixup',
               _('no conduit host specified in config; disabling fastlog\n'))
        return False
    return conduit

class remotefilectx(context.filectx):
    def __init__(self, repo, path, changeid=None, fileid=None,
                 filelog=None, changectx=None, ancestormap=None):
        if fileid == nullrev:
            fileid = nullid
        if fileid and len(fileid) == 40:
            fileid = bin(fileid)
        super(remotefilectx, self).__init__(repo, path, changeid,
            fileid, filelog, changectx)
        self._ancestormap = ancestormap

    def size(self):
        return self._filelog.size(self._filenode)

    @propertycache
    def _conduit(self):
        global conduit
        if conduit is None:
            conduit = createconduit(self._repo.ui)
        # If createconduit fails, conduit will be set to False. We use this to
        # avoid calling createconduit multiple times
        if conduit is False:
            return None
        return conduit

    @propertycache
    def _changeid(self):
        if '_changeid' in self.__dict__:
            return self._changeid
        elif '_changectx' in self.__dict__:
            return self._changectx.rev()
        elif '_descendantrev' in self.__dict__:
            # this file context was created from a revision with a known
            # descendant, we can (lazily) correct for linkrev aliases
            linknode = self._adjustlinknode(self._path, self._filelog,
                                            self._filenode, self._descendantrev)
            return self._repo.changelog.rev(linknode)
        else:
            return self.linkrev()

    def filectx(self, fileid, changeid=None):
        '''opens an arbitrary revision of the file without
        opening a new filelog'''
        return remotefilectx(self._repo, self._path, fileid=fileid,
                             filelog=self._filelog, changeid=changeid)

    def linkrev(self):
        return self._linkrev

    @propertycache
    def _linkrev(self):
        if self._fileid == nullid:
            return nullrev

        ancestormap = self.ancestormap()
        p1, p2, linknode, copyfrom = ancestormap[self._fileid]
        rev = self._repo.changelog.nodemap.get(linknode)
        if rev is not None:
            return rev

        # Search all commits for the appropriate linkrev (slow, but uncommon)
        path = self._path
        fileid = self._fileid
        cl = self._repo.unfiltered().changelog
        mfl = self._repo.manifestlog

        for rev in range(len(cl) - 1, 0, -1):
            node = cl.node(rev)
            data = cl.read(node) # get changeset data (we avoid object creation)
            if path in data[3]: # checking the 'files' field.
                # The file has been touched, check if the hash is what we're
                # looking for.
                if fileid == mfl[data[0]].readfast().get(path):
                    return rev

        # Couldn't find the linkrev. This should generally not happen, and will
        # likely cause a crash.
        return None

    def introrev(self):
        """return the rev of the changeset which introduced this file revision

        This method is different from linkrev because it take into account the
        changeset the filectx was created from. It ensures the returned
        revision is one of its ancestors. This prevents bugs from
        'linkrev-shadowing' when a file revision is used by multiple
        changesets.
        """
        lkr = self.linkrev()
        attrs = vars(self)
        noctx = not ('_changeid' in attrs or '_changectx' in attrs)
        if noctx or self.rev() == lkr:
            return lkr
        linknode = self._adjustlinknode(self._path, self._filelog,
                                        self._filenode, self.rev(),
                                        inclusive=True)
        return self._repo.changelog.rev(linknode)

    def renamed(self):
        """check if file was actually renamed in this changeset revision

        If rename logged in file revision, we report copy for changeset only
        if file revisions linkrev points back to the changeset in question
        or both changeset parents contain different file revisions.
        """
        ancestormap = self.ancestormap()

        p1, p2, linknode, copyfrom = ancestormap[self._filenode]
        if not copyfrom:
            return None

        renamed = (copyfrom, p1)
        if self.rev() == self.linkrev():
            return renamed

        name = self.path()
        fnode = self._filenode
        for p in self._changectx.parents():
            try:
                if fnode == p.filenode(name):
                    return None
            except error.LookupError:
                pass
        return renamed

    def ancestormap(self):
        if not self._ancestormap:
            self._ancestormap = self.filelog().ancestormap(self._filenode)

        return self._ancestormap

    def parents(self):
        repo = self._repo
        ancestormap = self.ancestormap()

        p1, p2, linknode, copyfrom = ancestormap[self._filenode]
        results = []
        if p1 != nullid:
            path = copyfrom or self._path
            flog = repo.file(path)
            p1ctx = remotefilectx(repo, path, fileid=p1, filelog=flog,
                                  ancestormap=ancestormap)
            p1ctx._descendantrev = self.rev()
            results.append(p1ctx)

        if p2 != nullid:
            path = self._path
            flog = repo.file(path)
            p2ctx = remotefilectx(repo, path, fileid=p2, filelog=flog,
                                  ancestormap=ancestormap)
            p2ctx._descendantrev = self.rev()
            results.append(p2ctx)

        return results

    def _nodefromancrev(self, ancrev, cl, mfl, path, fnode):
        """returns the node for <path> in <ancrev> if content matches <fnode>"""
        ancctx = cl.read(ancrev) # This avoids object creation.
        manifestnode, files = ancctx[0], ancctx[3]
        # If the file was touched in this ancestor, and the content is similar
        # to the one we are searching for.
        if path in files and fnode == mfl[manifestnode].readfast().get(path):
            return cl.node(ancrev)
        return None

    def _adjustlinknode(self, path, filelog, fnode, srcrev, inclusive=False):
        """return the first ancestor of <srcrev> introducing <fnode>

        If the linkrev of the file revision does not point to an ancestor of
        srcrev, we'll walk down the ancestors until we find one introducing
        this file revision.

        :repo: a localrepository object (used to access changelog and manifest)
        :path: the file path
        :fnode: the nodeid of the file revision
        :filelog: the filelog of this path
        :srcrev: the changeset revision we search ancestors from
        :inclusive: if true, the src revision will also be checked

        Note: This is based on adjustlinkrev in core, but it's quite different.

        adjustlinkrev depends on the fact that the linkrev is the bottom most
        node, and uses that as a stopping point for the ancestor traversal. We
        can't do that here because the linknode is not guaranteed to be the
        bottom most one.

        In our code here, we actually know what a bunch of potential ancestor
        linknodes are, so instead of stopping the cheap-ancestor-traversal when
        we get to a linkrev, we stop when we see any of the known linknodes.
        """
        repo = self._repo
        cl = repo.unfiltered().changelog
        mfl = repo.manifestlog
        ancestormap = self.ancestormap()
        linknode = ancestormap[fnode][2]

        if srcrev is None:
            # wctx case, used by workingfilectx during mergecopy
            revs = [p.rev() for p in self._repo[None].parents()]
            inclusive = True # we skipped the real (revless) source
        else:
            revs = [srcrev]

        if self._verifylinknode(revs, linknode):
            return linknode

        pc = repo._phasecache
        seenpublic = False
        iteranc = cl.ancestors(revs, inclusive=inclusive)
        for ancrev in iteranc:
            # First, check locally-available history.
            lnode = self._nodefromancrev(ancrev, cl, mfl, path, fnode)
            if lnode is not None:
                return lnode

            # This next part is super non-obvious, so big comment block time!
            #
            # It is possible to get extremely bad performance here when a fairly
            # common set of circumstances occur when this extension is combined
            # with a server-side commit rewriting extension like pushrebase.
            #
            # First, an engineer creates Commit A and pushes it to the server.
            # While the server's data structure will have the correct linkrev
            # for the files touched in Commit A, the client will have the
            # linkrev of the local commit, which is "invalid" because it's not
            # an ancestor of the main line of development.
            #
            # The client will never download the remotefilelog with the correct
            # linkrev as long as nobody else touches that file, since the file
            # data and history hasn't changed since Commit A.
            #
            # After a long time (or a short time in a heavily used repo), if the
            # same engineer returns to change the same file, some commands --
            # such as amends of commits with file moves, logs, diffs, etc  --
            # can trigger this _adjustlinknode code. In those cases, finding
            # the correct rev can become quite expensive, as the correct
            # revision is far back in history and we need to walk back through
            # history to find it.
            #
            # In order to improve this situation, we force a prefetch of the
            # remotefilelog data blob for the file we were called on. We do this
            # at most once, when we first see a public commit in the history we
            # are traversing.
            #
            # Forcing the prefetch means we will download the remote blob even
            # if we have the "correct" blob in the local store. Since the union
            # store checks the remote store first, this means we are much more
            # likely to get the correct linkrev at this point.
            #
            # In rare circumstances (such as the server having a suboptimal
            # linkrev for our use case), we will fall back to the old slow path.
            #
            # We may want to add additional heuristics here in the future if
            # the slow path is used too much. One promising possibility is using
            # obsolescence markers to find a more-likely-correct linkrev.
            if not seenpublic and pc.phase(repo, ancrev) == phases.public:
                # If the commit is public and fastlog is enabled for this repo
                # then we will can try to fetch the right linknode via fastlog
                # since fastlog already has the right linkrev for all public
                # commits
                if repo.ui.configbool('fastlog', 'enabled'):
                    lnode = self._linknodeviafastlog(repo, path, ancrev, fnode,
                                                     cl, mfl)
                    if lnode:
                        repo.ui.log('linkrevfixup', _('success\n'))
                        return lnode
                seenpublic = True
                try:
                    repo.fileservice.prefetch([(path, hex(fnode))], force=True)

                    # Now that we've downloaded a new blob from the server,
                    # we need to rebuild the ancestor map to recompute the
                    # linknodes.
                    self._ancestormap = None
                    linknode = self.ancestormap()[fnode][2] # 2 is linknode
                    if self._verifylinknode(revs, linknode):
                        return linknode
                except Exception as e:
                    errormsg = ('warning: failed to prefetch filepath %s ' +
                                'while adjusting linknode %s (%s)\n(this is ' +
                                'generally benign but it may make ' +
                                'this operation take longer to calculate ' +
                                'things locally)')
                    repo.ui.warn(_(errormsg) % (path, hex(linknode), e))

        return linknode

    def _linknodeviafastlog(self, repo, path, srcrev, fnode, cl, mfl):
        reponame = repo.ui.config('fbconduit', 'reponame')
        if self._conduit is None:
            return None
        try:
            srchex = repo[srcrev].hex()
            results = self._conduit.call_conduit(
                'scmquery.log_v2',
                timeout=FASTLOG_TIMEOUT_IN_SECS,
                repo=reponame,
                scm_type='hg',
                rev=srchex,
                file_paths=[path],
                skip=0,
            )
            if results is None:
                repo.ui.log('linkrevfixup',
                            _('fastlog returned 0 results\n'))
                return None
            for anc in results:
                ancrev = repo[str(anc['hash'])].rev()
                lnode = self._nodefromancrev(ancrev, cl, mfl, path, fnode)
                if lnode is not None:
                    return lnode
            return None
        except Exception as e:
            repo.ui.log('linkrevfixup',
                        _('call to fastlog failed (%s)\n') % e)
            return None

    def _verifylinknode(self, revs, linknode):
        """
        Check if a linknode is correct one for the current history.

        That is, return True if the linkrev is the ancestor of any of the
        passed in revs, otherwise return False.

        `revs` is a list that usually has one element -- usually the wdir parent
        or the user-passed rev we're looking back from. It may contain two revs
        when there is a merge going on, or zero revs when a root node with no
        parents is being created.
        """
        if not revs:
            return False
        try:
            # Use the C fastpath to check if the given linknode is correct.
            cl = self._repo.changelog
            return any(cl.isancestor(linknode, cl.node(r)) for r in revs)
        except error.LookupError:
            # The linknode read from the blob may have been stripped or
            # otherwise not present in the repository anymore. Do not fail hard
            # in this case. Instead, return false and continue the search for
            # the correct linknode.
            return False

    def ancestors(self, followfirst=False):
        ancestors = []
        queue = collections.deque((self,))
        seen = set()
        while queue:
            current = queue.pop()
            if current.filenode() in seen:
                continue
            seen.add(current.filenode())

            ancestors.append(current)

            parents = current.parents()
            first = True
            for p in parents:
                if first or not followfirst:
                    queue.append(p)
                first = False

        # Remove self
        ancestors.pop(0)

        # Sort by linkrev
        # The copy tracing algorithm depends on these coming out in order
        ancestors = sorted(ancestors, reverse=True, key=lambda x:x.linkrev())

        for ancestor in ancestors:
            yield ancestor

    def ancestor(self, fc2, actx):
        # the easy case: no (relevant) renames
        if fc2.path() == self.path() and self.path() in actx:
            return actx[self.path()]

        # the next easiest cases: unambiguous predecessor (name trumps
        # history)
        if self.path() in actx and fc2.path() not in actx:
            return actx[self.path()]
        if fc2.path() in actx and self.path() not in actx:
            return actx[fc2.path()]

        # do a full traversal
        amap = self.ancestormap()
        bmap = fc2.ancestormap()

        def parents(x):
            f, n = x
            p = amap.get(n) or bmap.get(n)
            if not p:
                return []

            return [(p[3] or f, p[0]), (f, p[1])]

        a = (self.path(), self.filenode())
        b = (fc2.path(), fc2.filenode())
        result = ancestor.genericancestor(a, b, parents)
        if result:
            f, n = result
            r = remotefilectx(self._repo, f, fileid=n,
                                 ancestormap=amap)
            return r

        return None

    def annotate(self, follow=False, linenumber=None, skiprevs=None,
                 diffopts=None, prefetchskip=None):
        introctx = self
        if prefetchskip:
            # use introrev so prefetchskip can be accurately tested
            introrev = self.introrev()
            if self.rev() != introrev:
                introctx = remotefilectx(self._repo, self._path,
                                         changeid=introrev,
                                         fileid=self._fileid,
                                         filelog=self._filelog,
                                         ancestormap=self._ancestormap)

        # like self.ancestors, but append to "fetch" and skip visiting parents
        # of nodes in "prefetchskip".
        fetch = []
        seen = set()
        queue = collections.deque((introctx,))
        seen.add(introctx.node())
        while queue:
            current = queue.pop()
            if current.filenode() != self.filenode():
                # this is a "joint point". fastannotate needs contents of
                # "joint point"s to calculate diffs for side branches.
                fetch.append((current.path(), hex(current.filenode())))
            if prefetchskip and current in prefetchskip:
                continue
            for parent in current.parents():
                if parent.node() not in seen:
                    seen.add(parent.node())
                    queue.append(parent)

        self._repo.ui.debug('remotefilelog: prefetching %d files '
                            'for annotate\n' % len(fetch))
        if fetch:
            self._repo.fileservice.prefetch(fetch)
        return super(remotefilectx, self).annotate(follow, linenumber,
                                                   skiprevs=skiprevs,
                                                   diffopts=diffopts)

    # Return empty set so that the hg serve and thg don't stack trace
    def children(self):
        return []

class remoteworkingfilectx(context.workingfilectx, remotefilectx):
    def __init__(self, repo, path, filelog=None, workingctx=None):
        self._ancestormap = None
        return super(remoteworkingfilectx, self).__init__(repo, path,
            filelog, workingctx)

    def parents(self):
        return remotefilectx.parents(self)

    def ancestormap(self):
        if not self._ancestormap:
            path = self._path
            pcl = self._changectx._parents
            renamed = self.renamed()

            if renamed:
                p1 = renamed
            else:
                p1 = (path, pcl[0]._manifest.get(path, nullid))

            p2 = (path, nullid)
            if len(pcl) > 1:
                p2 = (path, pcl[1]._manifest.get(path, nullid))

            m = {}
            if p1[1] != nullid:
                p1ctx = self._repo.filectx(p1[0], fileid=p1[1])
                m.update(p1ctx.filelog().ancestormap(p1[1]))

            if p2[1] != nullid:
                p2ctx = self._repo.filectx(p2[0], fileid=p2[1])
                m.update(p2ctx.filelog().ancestormap(p2[1]))

            copyfrom = ''
            if renamed:
                copyfrom = renamed[0]
            m[None] = (p1[1], p2[1], nullid, copyfrom)
            self._ancestormap = m

        return self._ancestormap
