# Compiled metadata batch: build and interface plan

Status: planning completed on 2026-10-05; installation and implementation are
proposed, not performed. Ryan authorized continuation from the accounting
reassessment into this plan. No execution allowance or Git permission is added.

## Decision and purpose

Build a small CPython C extension that performs sequential fresh file queries
in batches of at most 128 names. Keep discovery and the accounting algorithm in
Python. This can reduce Python loop and ctypes conversion overhead; it cannot
remove kernel-query cost. Speed remains unproved, including the cost of calling
the Python deadline checker for each file.

The completed by-name component remains a valid negative speed result. Its
correctness evidence informs the interface, but does not validate a new binary.
No old test, fixture, timing series or failed attempt is reopened by this plan.

## Verified local prerequisites

The explicit project interpreter is `.venv\Scripts\python.exe`, CPython
3.11.15, 64-bit AMD64, built with MSC v.1944. Its base installation is
`C:\Users\Ryan\AppData\Roaming\uv\python\cpython-3.11-windows-x86_64-none`.
`include\Python.h`, `include\pyconfig.h`, `libs\python311.lib`, `python311.dll`
and `libs\python3.lib` exist. The reported extension suffix is
`.cp311-win_amd64.pyd`. Presence and interpreter build metadata were checked;
these dependency files were not hashed or executed as build tools.

No usable compiler or Windows SDK was found in the checked PATH, known Visual
Studio/LLVM/MinGW/MSYS2/Scoop/Rust locations or Visual Studio/Windows Kits
registry roots. This is a bounded inventory, not an exhaustive disk search.
`winget.exe` is on PATH but was not invoked. Registered Visual C++ 14.50.35719
runtimes and VS Code are not compiler/SDK installations. There is no repository
`pyproject.toml`, `setup.py` or `setup.cfg` to extend.

The detailed inventory and preparation receipt are under
`../data/outputs/t/ebcb_plan_fa730bcb6d2e/`. No installer was downloaded or run.

## Proposed installation, after approval

Use Microsoft's fixed-version **Visual Studio 2022 Build Tools 17.14.41**
bootstrapper, build 17.14.37710.0, published September 15, 2026. Select its Build
Tools link in the fixed-version table, not the evergreen link. Record that row,
the resolved URL, SHA-256, valid Microsoft Authenticode signature and raw
ProductVersion/FileVersion metadata. Reconcile the metadata with the selected
distribution; do not assume the raw bootstrapper version string literally
equals the release or installed build number. Verify the installed instance
reports build 17.14.37710.0 before building. See the official
[release history](https://learn.microsoft.com/en-us/visualstudio/releases/2022/release-history).

Request these VS 2022 component identifiers:

| Selection | Identifier |
| --- | --- |
| C++ build workload, required dependencies only | `Microsoft.VisualStudio.Workload.VCTools` |
| MSVC v143 x64/x86 compiler and linker | `Microsoft.VisualStudio.Component.VC.Tools.x86.x64` |
| One Windows 11 SDK family | `Microsoft.VisualStudio.Component.Windows11SDK.26100` |

These identifiers are from the VS 2022 section of Microsoft's
[Build Tools component directory](https://learn.microsoft.com/en-us/visualstudio/install/workload-component-id-vs-build-tools?view=vs-2022).
Do not add `--includeRecommended` or `--includeOptional`. Workload-required
dependencies still include build infrastructure and runtime components; this
does not mean only two packages will be installed. The SDK identifier selects
a family; record the resolved SDK and compiler package versions after setup.
Require the selected installer/catalog to resolve all three requested IDs;
unavailable components do not authorize substitutions or extra workloads.

Use `--passive --wait --norestart` and the three `--add` selections above.
Microsoft documents these [installer parameters](https://learn.microsoft.com/en-us/visualstudio/install/use-command-line-parameters-to-install-visual-studio?view=vs-2022).
Use the normal Build Tools instance location after checking it is not an
existing installation to modify. Inspect the installer estimate and free space
before launching the passive install; that noninteractive command is not an
estimate/approval screen. Actual download/cache/installed sizes are not yet known.
Keep the existing 10 GiB free-space floor. Setup may need administrator consent
and may service shared runtimes. Do not request a runtime downgrade, automatic
restart, unrelated workloads or cleanup of existing software. A reboot-required
result is recorded and must be resolved before declaring the toolchain ready.

Keep the downloaded installer, signature/version record and setup log references
in a fresh ignored administration directory. Windows Installer may also use its
normal system caches/log locations. Installation is a machine change, not a
scientific experiment or a charge against a consumed query-series allocation.

## Isolated build

Proposed new create-only root: `data/outputs/t/ebcb_src_fa730bcb6d2e/`, subject to
an absence check immediately before creation. Keep versioned source revisions,
build scripts, objects, import libraries, PDBs, binaries, temporary files and
logs there. Do not overwrite any prior candidate or install into site-packages.

Use a single C implementation with public CPython 3.11 APIs, the existing Python
headers and `python311.lib`, x64 MSVC v143, and the selected SDK. Build a
`.cp311-win_amd64.pyd` using `/LD /MD /O2 /W4`, explicit include/library paths,
explicit output paths and `Kernel32.lib`. Freeze the complete actual command
before building. `/MD` explicitly selects the DLL runtime; see Microsoft's
[runtime-library flags](https://learn.microsoft.com/en-us/cpp/build/reference/md-mt-ld-use-run-time-library?view=msvc-170).
Use Python's documented [Windows extension model](https://docs.python.org/3.11/extending/windows.html),
not private CPython internals or a raw-source retrieval workaround.

Record source/build-script hashes, compiler/linker/SDK paths and versions,
relevant headers/import-library/runtime hashes, flags, logs and final binary
hash. Inspect target architecture, module export and DLL dependencies before
loading by explicit absolute path. Preserve each failed build/log and assign a
new revision for a routine correction. Reproducible build instructions are
required; byte-identical builds are not claimed without evidence. This is a
CPython 3.11/x64 binary, not an `abi3` portability promise.

## Frozen candidate interface

```python
query_batch(prefix: str, names: tuple[str, ...], check_deadline: callable)
    -> tuple[(volume64, file64, logical_size, opaque_id128_bytes), ...]
```

The Python wrapper supplies one normalized absolute directory prefix and at
most 128 bare names, retaining their order and duplicate-name occurrences.
The returned tuple has exactly one record per input name, or the call raises
without returning partial results. Empty input returns an empty tuple after a
deadline check. Reject non-string input, embedded NULs, separators, `.`/`..`,
alternate-stream syntax and unsupported path forms before any native query.
Check Unicode lengths and all buffer/allocation arithmetic, including the
terminator and extended-path prefix, before allocating. Define and test the
supported Windows path length during source review; never truncate a path.

Use `PyUnicode_AsWideCharString` with matching `PyMem_Free`, public Python object
construction and `PyObject_CallNoArgs`. Maintain explicit reference/buffer
ownership on success, callback error, native error and allocation failure.
Do not expose a background worker, partial-success option or unchecked pointer.
The GIL is held for Python callbacks and object operations; any release around
the Windows call must capture its last error before reacquiring it.

Each name gets a fresh `GetFileInformationByName` query with the reviewed
104-byte x64 `FILE_STAT_BASIC_INFORMATION` layout. Assert structure size and
field offsets at build time. Resolve the API only in an authorized live query
unit; import, ABI inspection and artificial tests must not issue live queries.
Fail closed if the API/ABI is unavailable. Its official documentation carries
a prerelease notice; no broader Windows/platform support is claimed. See
[GetFileInformationByName](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-getfileinformationbyname).

Return the complete unsigned 64-bit native volume and file identifiers,
nonnegative logical size and opaque 16-byte file identifier from that same
query. Do not truncate, mask, map to `os.stat` numeric labels or perform a second
query for the 128-bit field. Python accounting uses the first three values; the
opaque field permits correctness auditing. Its allocation cost remains in
future timing. Overall inventory counts/totals remain unbounded Python integers.
Retain local fixed-NTFS, ancestor/reparse and returned-type/attribute guards from
the reviewed adapter; reject unsupported indirection rather than following it.

## Accounting and deadline behavior

Python retains `os.walk`, complete inventory dictionaries, identity continuity,
per-name hard-link multiplicity, conservative maximum sizes, disappearance
resets and acceptance. Enumeration supplies names only, never cached sizes.
Two complete inventories must still satisfy the existing acceptance relation.
The wrapper must not combine records from incompatible identity backends.

Create the deadline once as `time.monotonic() + 0.5` and pass the same closure to
every batch, directory and restarted inventory. It covers discovery, queries,
aggregation and acceptance. No batch-local deadline or different native clock
is introduced. Call the checker before each query and after each successful
query, then again before returning the complete batch. Keep the Python checks
around discovery/aggregation/acceptance too. A blocking Windows call cannot be
preempted by these checks; the original process supervision still applies.

Preserve the original exception precedence: if the native query fails, capture
its error immediately and raise the corresponding Windows `OSError` with its
Unicode filename. Do not replace it with a later deadline-callback exception.
This matches the original `os.stat` failure path, which skips its post-query
check. The outer `FileNotFoundError` handler discards the whole incomplete
inventory and checks the unchanged deadline before trying again; other errors
propagate. A successful query followed by a failing callback returns no batch.
Cleanup must preserve the selected exception. Use the public
[exception API](https://docs.python.org/3.11/c-api/exceptions.html) for translation.

## Proposed next authorized block

After Ryan approves installation and isolated implementation:

1. Verify installer provenance, install the specified tools, and record the
   installed compiler/SDK/runtime state. Do not begin if signature, target or
   free-space checks show a material discrepancy.
2. Implement and independently review the isolated extension, build script,
   wrapper and artificial test provider. Compile the production extension and
   a separate test variant sharing its conversion/query-loop core. Test hooks
   must not be exposed by the production module.
3. Validate the compiled core using scripted provider responses, with the live
   query provider disabled in the test variant. Cover 0/1/128/129 names, Unicode,
   malformed paths, integer limits, identity/size preservation, missing/access
   errors, late errors, callback failures at each boundary and cleanup. Fake
   enumerator/provider cases check complete inventories, hard links, growth,
   disappearance/restart and deadline behavior. These are artificial checks,
   not evidence that the Windows API or real filesystem behavior is correct.
4. Run focused validation first, then the project full suite once for the new
   implementation, using the explicit project interpreter, `-B`,
   `PYTHONDONTWRITEBYTECODE=1` and `PYTHONUTF8=1`. Keep logs/results ignored.
   Preserve failures; routine source/build corrections may proceed within this
   block under Ryan's standing rule. Material accounting, evidence or resource
   problems need investigation. Do not rerun unchanged historical component
   suites or experiments merely for this new session.
5. Freeze the reviewed source/binary hashes and report build/artificial-test
   results. Before any live candidate query, propose a separate supervised
   correctness/performance series with a fresh explicit envelope and prospective
   criteria. Existing series have zero attempts left; leftover arithmetic time
   does not create a new attempt. No native speed measurement follows from this
   installation/prototype block.

No runtime scanner replacement or scientific recovery is included. Native
correctness, component speed, complete scanner readiness, integration/regression
and the recovery certificate must precede real execution. The existing 30-call
static gate below 0.40 seconds, dynamic per-scan gate below 0.40 seconds with
monitor intervals below 0.90 seconds, and live 0.5/1-second limits remain.

## Preservation and project position

Whole-root output cap: 32 GiB; owned worker-tree memory cap: 8 GiB; free-space
floor: 10 GiB. Real diagnostic and cumulative balances stay
`292.73500000001513` and `11132.492000000013` seconds. No consumed allocation is
renewed. Nine embargoes, three sealed holdouts, six retention reviews, twelve
earlier YOLO reviews and all failed/completed evidence remain preserved. No
scientific body or old fixture is read or hashed in this planning task.

The next scientific result remains the planned 48-row breakdown of saved ball
candidate errors. Three-possession player coordinates are complete. Reliable
ball tracking/quality gates, possession understanding, roster identity, matchups
and defensive scoring remain later work. This plan addresses accounting
infrastructure; it adds no scientific result or measured speed improvement.

Planning changes are this note plus continuation entries in current state,
roadmap and validation history. Starting state: 22 intended unstaged files,
empty index, branch `codex/ball-detector-baseline`, HEAD
`fa730bcb6d2e6d396391191c0fb3e36a3a338bf1`. Expected final state: 23 intended
unstaged files, unchanged branch/HEAD/index. Staging, committing, pushing, PR
creation and merging still require their own explicit authorization.
