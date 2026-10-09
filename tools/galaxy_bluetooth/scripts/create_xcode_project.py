#!/usr/bin/env python3
"""Reproducibly generate the dependency-free Xcode project."""
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "ios"
PROJECT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "GalaxyBluetooth.xcodeproj"
PROJECT.mkdir(exist_ok=True)


def uid(name):
    return hashlib.sha256(name.encode()).hexdigest()[:24].upper()


objects = []


def obj(name, value):
    objects.append(f"\t\t{uid(name)} = {{ {value} }};")
    return uid(name)


files = sorted((ROOT / "GalaxyBluetooth").glob("*.swift"))
for file in files:
    obj(file.name, f'isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = "{file.name}"; sourceTree = "<group>";')
    obj("build-" + file.name, f'isa = PBXBuildFile; fileRef = {uid(file.name)};')
obj("plist", 'isa = PBXFileReference; lastKnownFileType = text.plist.xml; path = Info.plist; sourceTree = "<group>";')
obj("web", 'isa = PBXFileReference; lastKnownFileType = folder; path = Resources/Web; sourceTree = "<group>";')
obj("build-web", f'isa = PBXBuildFile; fileRef = {uid("web")};')
obj("branding", 'isa = PBXFileReference; lastKnownFileType = folder.assetcatalog; path = Resources/Branding.xcassets; sourceTree = "<group>";')
obj("build-branding", f'isa = PBXBuildFile; fileRef = {uid("branding")};')
obj("app", 'isa = PBXFileReference; explicitFileType = wrapper.application; path = GalaxyBluetooth.app; sourceTree = BUILT_PRODUCTS_DIR;')
obj("code-group", 'isa = PBXGroup; children = (' + ','.join([uid(f.name) for f in files] + [uid("plist"), uid("web"), uid("branding")]) + '); path = GalaxyBluetooth; sourceTree = "<group>";')
obj("products", f'isa = PBXGroup; children = ({uid("app")}); name = Products; sourceTree = "<group>";')
obj("root-group", f'isa = PBXGroup; children = ({uid("code-group")},{uid("products")}); sourceTree = "<group>";')
obj("sources", 'isa = PBXSourcesBuildPhase; buildActionMask = 2147483647; files = (' + ','.join(uid("build-" + f.name) for f in files) + '); runOnlyForDeploymentPostprocessing = 0;')
obj("resources", f'isa = PBXResourcesBuildPhase; buildActionMask = 2147483647; files = ({uid("build-web")},{uid("build-branding")}); runOnlyForDeploymentPostprocessing = 0;')
obj("frameworks", 'isa = PBXFrameworksBuildPhase; buildActionMask = 2147483647; files = (); runOnlyForDeploymentPostprocessing = 0;')
for configuration in ("Debug", "Release"):
    obj("project-" + configuration, f'isa = XCBuildConfiguration; name = {configuration}; buildSettings = {{ SDKROOT = iphoneos; IPHONEOS_DEPLOYMENT_TARGET = 17.0; CLANG_ENABLE_MODULES = YES; }};')
    optimization = "-Onone" if configuration == "Debug" else "-O"
    obj("target-" + configuration, f'''isa = XCBuildConfiguration; name = {configuration}; buildSettings = {{
      ASSETCATALOG_COMPILER_APPICON_NAME = AppIcon;
      PRODUCT_NAME = "$(TARGET_NAME)";
      PRODUCT_BUNDLE_IDENTIFIER = link.galaxy.bluetooth;
      INFOPLIST_FILE = GalaxyBluetooth/Info.plist;
      GENERATE_INFOPLIST_FILE = NO;
      SWIFT_VERSION = 5.0;
      SWIFT_OPTIMIZATION_LEVEL = "{optimization}";
      TARGETED_DEVICE_FAMILY = 1;
      IPHONEOS_DEPLOYMENT_TARGET = 17.0;
      SUPPORTED_PLATFORMS = "iphoneos iphonesimulator";
      CODE_SIGN_STYLE = Automatic;
      ENABLE_USER_SCRIPT_SANDBOXING = YES;
    }};''')
for owner in ("project", "target"):
    obj(owner + "-configurations", f'isa = XCConfigurationList; buildConfigurations = ({uid(owner + "-Debug")},{uid(owner + "-Release")}); defaultConfigurationIsVisible = 0; defaultConfigurationName = Release;')
obj("target", f'''isa = PBXNativeTarget; name = GalaxyBluetooth; productName = GalaxyBluetooth;
  productReference = {uid("app")}; productType = "com.apple.product-type.application";
  buildConfigurationList = {uid("target-configurations")};
  buildPhases = ({uid("sources")},{uid("frameworks")},{uid("resources")}); buildRules = (); dependencies = ();''')
obj("project", f'''isa = PBXProject; attributes = {{ LastUpgradeCheck = 1600; }};
  buildConfigurationList = {uid("project-configurations")}; compatibilityVersion = "Xcode 14.0";
  developmentRegion = en; knownRegions = (en, Base); mainGroup = {uid("root-group")};
  productRefGroup = {uid("products")}; projectDirPath = ""; projectRoot = ""; targets = ({uid("target")});''')
(PROJECT / "project.pbxproj").write_text('// !$*UTF8*$!\n{ archiveVersion = 1; classes = {}; objectVersion = 56; objects = {\n' + '\n'.join(objects) + f'\n}}; rootObject = {uid("project")}; }}\n')
schemes = PROJECT / "xcshareddata/xcschemes"
schemes.mkdir(parents=True, exist_ok=True)
reference = f'<BuildableReference BuildableIdentifier="primary" BlueprintIdentifier="{uid("target")}" BuildableName="GalaxyBluetooth.app" BlueprintName="GalaxyBluetooth" ReferencedContainer="container:GalaxyBluetooth.xcodeproj"/>'
(schemes / "GalaxyBluetooth.xcscheme").write_text(f'''<?xml version="1.0" encoding="UTF-8"?>
<Scheme LastUpgradeVersion="1600" version="1.3">
  <BuildAction parallelizeBuildables="YES" buildImplicitDependencies="YES"><BuildActionEntries><BuildActionEntry buildForTesting="YES" buildForRunning="YES" buildForProfiling="YES" buildForArchiving="YES" buildForAnalyzing="YES">{reference}</BuildActionEntry></BuildActionEntries></BuildAction>
  <LaunchAction buildConfiguration="Debug" selectedDebuggerIdentifier="Xcode.DebuggerFoundation.Debugger.LLDB" selectedLauncherIdentifier="Xcode.IDEFoundation.Launcher.LLDB" launchStyle="0" useCustomWorkingDirectory="NO" ignoresPersistentStateOnLaunch="NO" debugDocumentVersioning="YES" debugServiceExtension="internal" allowLocationSimulation="YES"><BuildableProductRunnable runnableDebuggingMode="0">{reference}</BuildableProductRunnable></LaunchAction>
  <ProfileAction buildConfiguration="Release" shouldUseLaunchSchemeArgsEnv="YES" savedToolIdentifier="" useCustomWorkingDirectory="NO" debugDocumentVersioning="YES"><BuildableProductRunnable runnableDebuggingMode="0">{reference}</BuildableProductRunnable></ProfileAction>
  <AnalyzeAction buildConfiguration="Debug"/>
  <ArchiveAction buildConfiguration="Release" revealArchiveInOrganizer="YES"/>
</Scheme>''')
print(PROJECT)
