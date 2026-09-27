$ErrorActionPreference = 'Stop'
$managed = 'C:/Program Files/Unity/Hub/Editor/6000.5.7f1/Editor/Data/Managed'
$target = Join-Path $managed 'UnityEngine/UnityEditor.CoreModule.dll'
$cecil = Join-Path $managed 'Unity.Cecil.dll'
[void][Reflection.Assembly]::LoadFrom($cecil)
$assembly = [Mono.Cecil.AssemblyDefinition]::ReadAssembly($target)
try {
    $model = $assembly.MainModule.Types | Where-Object FullName -eq 'UnityEditor.ModelImporter'
    $importer = $assembly.MainModule.Types | Where-Object FullName -eq 'UnityEditor.AssetImporter'
    $identifier = $importer.NestedTypes | Where-Object Name -eq 'SourceAssetIdentifier'
    $properties = @($model.Properties | Where-Object Name -match 'sourceMaterials|materialImportMode|materialLocation' | ForEach-Object {
        [ordered]@{ name = $_.Name; type = $_.PropertyType.FullName; getterPublic = $_.GetMethod.IsPublic; getterInternal = $_.GetMethod.IsAssembly }
    })
    $constructors = @($identifier.Methods | Where-Object Name -eq '.ctor' | ForEach-Object {
        [ordered]@{ method = $_.FullName; isPublic = $_.IsPublic; il = @($_.Body.Instructions | ForEach-Object ToString) }
    })
    $methods = @($importer.Methods | Where-Object { $_.IsPublic -and $_.Name -match 'GetExternalObjectMap|AddRemap|RemoveRemap|SaveAndReimport' } | ForEach-Object FullName)
    $receipt = [ordered]@{
        scope = 'Offline metadata inspection of installed Unity assembly via Cecil. No Editor process, Unity API getter or native method invoked.'
        assembly = [ordered]@{ path = $target; sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $target).Hash.ToLowerInvariant(); mvid = $assembly.MainModule.Mvid.ToString() }
        metadataReader = [ordered]@{ path = $cecil; sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $cecil).Hash.ToLowerInvariant() }
        properties = $properties
        publicRemapMethods = $methods
        sourceIdentifierConstructors = $constructors
        finding = 'ModelImporter.sourceMaterials is internal. Public SourceAssetIdentifier(Object) copies only type and current object name. It cannot recover original source names from a remapped external material.'
    }
    $output = Join-Path $PSScriptRoot 'installed-api.json'
    if (Test-Path -LiteralPath $output) { throw 'Frozen API audit exists; use a new destination for another inspection.' }
    $receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $output -Encoding utf8NoBOM
    Write-Output "Offline installed API audit saved: $output"
}
finally { $assembly.Dispose() }
