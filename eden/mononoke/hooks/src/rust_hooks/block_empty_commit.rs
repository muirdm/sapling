/*
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This software may be used and distributed according to the terms of the
 * GNU General Public License version 2.
 */

use crate::{
    ChangesetHook, CrossRepoPushSource, FileContentFetcher, HookExecution, HookRejectionInfo,
};
use anyhow::Error;
use async_trait::async_trait;
use bookmarks::BookmarkName;
use context::CoreContext;
use mononoke_types::BonsaiChangeset;

#[derive(Clone, Debug)]
pub struct BlockEmptyCommit;

impl BlockEmptyCommit {
    pub fn new() -> Self {
        Self
    }
}

#[async_trait]
impl ChangesetHook for BlockEmptyCommit {
    async fn run<'this: 'cs, 'ctx: 'this, 'cs, 'fetcher: 'cs>(
        &'this self,
        _ctx: &'ctx CoreContext,
        _bookmark: &BookmarkName,
        changeset: &'cs BonsaiChangeset,
        _content_fetcher: &'fetcher dyn FileContentFetcher,
        _cross_repo_push_source: CrossRepoPushSource,
    ) -> Result<HookExecution, Error> {
        if changeset.file_changes_map().is_empty() {
            Ok(HookExecution::Rejected(HookRejectionInfo::new_long(
                "Empty commit is not allowed",
                "You must include file changes in your commit for it to land".to_string(),
            )))
        } else {
            Ok(HookExecution::Accepted)
        }
    }
}
