# Windows desktop development setup

The primary client is Unity on **Windows 10/11 x64**. Web support follows later. Online multiplayer authority and player data belong to the existing OCI backend; offline LAN uses a separate local realm and must operate without Internet access. Setting up this checkout does not deploy or provision a backend.

## Source and assets

Install Git with Git LFS before checking out [racing-bois-codex](https://github.com/liquid8796/racing-bois-codex). The repository keeps large art sources and rendered evidence in LFS; pointer text is not a usable asset. From the checkout, hydrate and verify the assets:

```powershell
git lfs install --local
git lfs pull
git lfs fsck
```

Use the existing account/storage entitlement. Do not buy credits, enable paid services or provision cloud generation as part of setup. Keep the SHA256-bound concepts and evidence bytes unchanged. In particular, the user-owned `ArtSource/Weapons/RB_Club.blend` is protected at SHA256 `553f60a0bd9ab32413c3c584aa61cf5a4076752364efb4b8f0a92b567c67a37f`.

`ProjectSettings/ProjectVersion.txt` pins Unity **6000.5.7f1**. Install that editor with Windows build support using the normal Unity installation workflow. `global.json` selects .NET SDK **10.0.301**, allowing a later patch in that feature band. No editor, SDK, global configuration or environment variable is installed or changed by the dependency preflight below.

## Pinned direct Unity MCP package

This checkout uses the direct Unity MCP package, with the following exact source binding:

| Field | Required value |
| --- | --- |
| Repository | `https://github.com/liquid8796/unity-mcp.git` |
| Commit | `0f9776ffc5cc35c2e1482455178fde21c58e0b48` |
| Package | `com.coplaydev.unity-mcp` |
| Version | `10.2.1-beta.7` |
| Package directory | Sibling `unity-mcp/MCPForUnity` |

The checked-in manifest and lock currently declare `file:D:/Project/Unity/unity-mcp/MCPForUnity`, beside `D:/Project/Unity/racing-bois`. Verify the dependency before opening Unity:

```powershell
.\tools\bootstrap-unity-mcp.ps1
# Equivalent explicit mode:
.\tools\bootstrap-unity-mcp.ps1 -VerifyOnly
```

Default verification performs local reads only, using Git's `--no-optional-locks` option. It checks the exact sibling path, manifest/lock binding, ordinary Git repository root, clean working tree, origin URL, commit, package name and package version. It rejects linked paths, a different repository, a different revision, and staged/modified/untracked files. It does not discover or call any MCP service.

For a fresh machine where that sibling directory is completely absent, request installation explicitly:

```powershell
.\tools\bootstrap-unity-mcp.ps1 -Install
```

Only this mode can clone the exact remote, fetch the pinned commit and create a detached checkout. An existing directory is verified without fetching or changing it. The script never resets, pulls, deletes, cleans, overwrites user files, edits active package files, changes global Git configuration, or enables a paid service. If installation fails, any partial checkout is preserved for inspection and the next run refuses to replace it.

For another checkout location, the script derives `unity-mcp` beside that checkout and checks that both package files resolve to its `MCPForUnity` directory. The current absolute paths will fail that check if they refer elsewhere. Deliberately adapt both local package references as a separate reviewed configuration change before installation; this helper does not silently rewrite a running Unity project's dependency. Preserve any existing sibling directory and its local changes.

This helper only prepares/verifies the package checkout. It does not open Unity, enable a bridge, select an editor instance or claim a successful live MCP handshake. Use the direct Unity MCP workflow when editor automation is required. **Never use Jarvis MCP in Codex**, including discovery, read-only calls, delegated agents or bridges to Unity, Blender or image generation. Blender authoring uses the separately pinned [direct Blender MCP setup](../tools/blender/README.md), and image concepts use the built-in image tool.

## Local state and acceptance

`Library`, `Temp`, logs, builds, `_local`, local databases, certificates and original-game research extracts are intentionally ignored. A fresh clone does not include private realm data, credentials, generated builds, downloaded research/model caches or running services. Do not copy production data or secrets into source control to make a clone look complete. Recreate only the local tooling required by the relevant phase instructions; keep online and LAN realms separate.

P08 Golden sources, renders, descriptors and staging artifacts are **candidates**, including those with passing structural import/export receipts. Technical checks do not establish 100% concept fidelity. Keep mismatching assets unaccepted and compare actual corresponding-view renders with the exact pinned concepts before promotion. Mesh, UV, material, animation, performance, contact and visual gates have separate evidence requirements. Asset recovery uses local/free tools only.

Continue from [the current P08–P10 checkpoint](P08_P10_RUN.md) and the receipt belonging to the exact source revision. Historical demos and stored deployment receipts do not prove that a service or release is currently running.
