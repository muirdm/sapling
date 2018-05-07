// Copyright (c) 2018-present, Facebook, Inc.
// All Rights Reserved.
//
// This software may be used and distributed according to the terms of the
// GNU General Public License version 2 or any later version.

include "scm/mononoke/mononoke-types/if/mononoke_types_thrift.thrift"

typedef mononoke_types_thrift.Sha1 HgNodeHash (hs.newtype)

// Manifest contents are expected to generally be small, so they're stored
// inline in the envelope. There's also no real dedup possible between native
// Mononoke data structures and these ones.
struct HgManifestEnvelope {
  1: required HgNodeHash node_id,
  2: optional HgNodeHash p1,
  3: optional HgNodeHash p2,
  // Root tree manifest nodes can have node IDs that don't match the contents.
  // That is required for lookups, but it means that in the event of recovery
  // from a disaster, hash consistency can't be checked. The computed node ID
  // is stored to allow that to happen.
  4: required HgNodeHash computed_node_id,
  // These contents are exactly as they would be serialized by Mercurial.
  5: optional binary contents,
}

struct HgFileEnvelope {
  1: required HgNodeHash node_id,
  2: optional HgNodeHash p1,
  3: optional HgNodeHash p2,
  4: optional mononoke_types_thrift.ContentId content_id,
  // content_size is a u64 stored as an i64, and doesn't include the size of
  // the metadata
  5: required i64 content_size,
  6: optional binary metadata,
}
