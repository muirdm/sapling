use bytes::Bytes;
use error::Error;
use linked_hash_map::LinkedHashMap;
use std::convert::AsRef;
use std::ops::Range;
use std::path::{Path, PathBuf};
use std::sync::Arc;

/// Collection of config sections loaded from various sources.
#[derive(Default)]
pub struct ConfigSet {
    sections: LinkedHashMap<Bytes, Section>,
    errors: Vec<Error>,
}

/// Internal representation of a config section.
#[derive(Default)]
struct Section {
    items: LinkedHashMap<Bytes, Vec<ValueSource>>,
}

/// A config value with associated metadata like where it comes from.
#[derive(Clone)]
pub struct ValueSource {
    value: Option<Bytes>,
    source: Bytes, // global, user, repo, "--config", or an extension name, etc.
    location: Option<ValueLocation>,
}

/// The on-disk file name and byte offsets that provide the config value.
/// Useful if applications want to edit config values in-place.
#[derive(Clone)]
struct ValueLocation {
    path: Arc<PathBuf>,
    location: Range<usize>,
}

impl ConfigSet {
    /// Return an empty `ConfigSet`.
    pub fn new() -> Self {
        Default::default()
    }

    /// Load config files at given path. The path could be either a directory or a file.
    ///
    /// If `path` is a directory, files directly inside it with extension `.rc` will be loaded.
    /// Files in subdirectories are ignored. The order of loading them is undefined. If `path` is
    /// a file, it will be loaded directly.
    ///
    /// A config file can use `%include` to load other paths (directories or files). They will
    /// be loaded recursively. Includes take effect in place, instead of deferred. For example,
    /// with the following two files:
    ///
    /// ```plain,ignore
    /// ; This is 1.rc
    /// [section]
    /// x = 1
    /// %include 2.rc
    /// y = 2
    ///
    /// ; This is 2.rc
    /// [section]
    /// x = 3
    /// y = 4
    /// ```
    ///
    /// After loading `1.rc`. `x` is set to 3 and `y` is set to 2.
    ///
    /// Loading a file that is already parsed or being parsed by this `load_path` call is ignored,
    /// to avoid infinite loop. A separate `load_path` call would not ignore files loaded by
    /// other `load_path` calls.
    ///
    /// The `source` field is to extra information about who initialized the config loading. For
    /// example, "user_hgrc" indicates it is from user config file.
    ///
    /// Errors will be pushed to an internal array, and can be retrieved by `errors`. Non-existed
    /// path is not considered as an error.
    pub fn load_path(&mut self, path: &Path, source: &'static str) {
        unimplemented!()
    }

    /// Load content of an unnamed config file. The `ValueLocation`s of loaded config items will
    /// have an empty `path`.
    ///
    /// The `source` field is to extra information about who initialized the config loading. For
    /// example, "--config" indicates it is from the global "--config" flag, "env" indicates
    /// it is from environment variables (ex. "PAGER").
    ///
    /// Errors will be pushed to an internal array, and can be retrieved by `errors`.
    pub fn parse<B: Into<Bytes>, S: Into<Bytes>>(&mut self, content: B, source: S) {
        unimplemented!()
    }

    /// Get config sections.
    pub fn sections(&self) -> Vec<Bytes> {
        self.sections.keys().cloned().collect()
    }

    /// Get config names in the given section. Sorted by insertion order.
    pub fn keys<S: Into<Bytes>>(&self, section: S) -> Vec<Bytes> {
        self.sections
            .get(&section.into())
            .map(|section| section.items.keys().cloned().collect())
            .unwrap_or(Vec::new())
    }

    /// Get config value for a given config.
    /// Return `None` if the config item does not exist or is unset.
    pub fn get<S: Into<Bytes>, N: Into<Bytes>>(&self, section: S, name: N) -> Option<Bytes> {
        self.sections.get(&section.into()).and_then(|section| {
            section
                .items
                .get(&name.into())
                .and_then(|values| values.last().and_then(|value| value.value.clone()))
        })
    }

    /// Get detailed sources of a given config, including overrides, and source information.
    /// The last item in the returned vector is the latest value that is considered effective.
    ///
    /// Return an emtpy vector if the config does not exist.
    pub fn get_sources<S: Into<Bytes>, N: Into<Bytes>>(
        &self,
        section: S,
        name: N,
    ) -> Vec<ValueSource> {
        self.sections
            .get(&section.into())
            .and_then(|section| section.items.get(&name.into()).map(|values| values.clone()))
            .unwrap_or(Vec::new())
    }

    /// Set a config item directly. `section`, `name` locates the config. `value` is the new value.
    /// `source` is some annotation about who set it, ex. "reporc", "userrc", "--config", etc.
    pub fn set<T: Into<Bytes>, N: Into<Bytes>, S: Into<Bytes>>(
        &mut self,
        section: T,
        name: N,
        value: Option<&[u8]>,
        source: S,
    ) {
        let section = section.into();
        let name = name.into();
        let source = source.into();
        let value = value.map(|v| Bytes::from(v));
        self.set_internal(section, name, value, None, &source)
    }

    /// Get errors caused by parsing config files previously.
    pub fn errors(&self) -> &Vec<Error> {
        &self.errors
    }

    fn set_internal(
        &mut self,
        section: Bytes,
        name: Bytes,
        value: Option<Bytes>,
        location: Option<ValueLocation>,
        source: &Bytes,
    ) {
        self.sections
            .entry(section)
            .or_insert_with(|| Default::default())
            .items
            .entry(name)
            .or_insert_with(|| Vec::with_capacity(1))
            .push(ValueSource {
                value,
                location,
                source: source.clone(),
            })
    }
}

impl ValueSource {
    /// Return the actual value stored in this config value, or `None` if uset.
    pub fn value(&self) -> &Option<Bytes> {
        &self.value
    }

    /// Return the "source" information for the config value. It's usually who sets the config,
    /// like "--config", "user_hgrc", "system_hgrc", etc.
    pub fn source(&self) -> &Bytes {
        &self.source
    }

    /// Return the file path and byte range for the exact config value,
    /// or `None` if there is no such information.
    ///
    /// If the value is `None`, the byte range is for the "%unset" statement.
    pub fn location(&self) -> Option<(PathBuf, Range<usize>)> {
        match self.location {
            Some(ref src) => Some((src.path.as_ref().to_path_buf(), src.location.clone())),
            None => None,
        }
    }
}

/// C memchr-like API
#[inline]
fn memchr(needle: u8, haystack: &[u8]) -> Option<usize> {
    haystack.iter().position(|&x| x == needle)
}

/// Test if a binary char is a space.
#[inline]
fn is_space(byte: u8) -> bool {
    b" \t\r\n".contains(&byte)
}

/// Remove space characters from both ends. `start` position is inclusive, `end` is exclusive.
/// Return the stripped `start` and `end` offsets.
#[inline]
fn strip_offsets(buf: &Bytes, start: usize, end: usize) -> (usize, usize) {
    let mut start = start;
    let mut end = end;
    while start < end && is_space(buf[start]) {
        start += 1
    }
    while start < end && is_space(buf[end - 1]) {
        end -= 1
    }
    (start, end)
}

/// Strip spaces and return a `Bytes` sub-slice.
#[inline]
fn strip(buf: &Bytes, start: usize, end: usize) -> Bytes {
    let (start, end) = strip_offsets(buf, start, end);
    buf.slice(start, end)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_empty() {
        let cfg = ConfigSet::new();
        assert!(cfg.sections().is_empty());
        assert!(cfg.keys("foo").is_empty());
        assert!(cfg.get("foo", "bar").is_none());
        assert!(cfg.get_sources("foo", "bar").is_empty());
        assert!(cfg.errors().is_empty());
    }

    #[test]
    fn test_set() {
        let mut cfg = ConfigSet::new();
        cfg.set("y", "b", Some(b"1"), "set1");
        cfg.set("y", "b", Some(b"2"), "set2");
        cfg.set("y", "a", Some(b"3"), "set3");
        cfg.set("z", "p", Some(b"4"), "set4");
        cfg.set("z", "p", None, "set5");
        assert_eq!(cfg.sections(), vec![Bytes::from("y"), Bytes::from("z")]);
        assert_eq!(cfg.keys("y"), vec![Bytes::from("b"), Bytes::from("a")]);
        assert_eq!(cfg.get("y", "b"), Some(Bytes::from("2")));
        assert_eq!(cfg.get("y", "a"), Some(Bytes::from("3")));
        assert_eq!(cfg.get("z", "p"), None);

        let sources = cfg.get_sources("z", "p");
        assert_eq!(sources.len(), 2);
        assert_eq!(sources[0].value(), &Some(Bytes::from("4")));
        assert_eq!(sources[1].value(), &None);
        assert_eq!(sources[0].source(), "set4");
        assert_eq!(sources[1].source(), "set5");
        assert_eq!(sources[0].location(), None);
        assert_eq!(sources[1].location(), None);
    }
}
