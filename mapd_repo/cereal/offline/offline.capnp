using Go = import "/go.capnp";
@0xda3a0d9284ca402f;
$Go.package("offline");
$Go.import("pfeifer.dev/mapd/cereal/offline");

# WARNING: must be kept in perfect sync (names and values) with the
# HighwayClass enum in cereal/custom/custom.capnp — state.go casts directly
# between the two generated enum types.
enum HighwayClass {
  unknown @0;
  motorway @1;
  motorwayLink @2;
  trunk @3;
  trunkLink @4;
  primary @5;
  primaryLink @6;
  secondary @7;
  secondaryLink @8;
  tertiary @9;
  tertiaryLink @10;
  unclassified @11;
  residential @12;
  livingStreet @13;
}

struct Way {
  name @0 :Text;
  ref @1 :Text;
  maxSpeed @2 :Float64;
  minLat @3 :Float64;
  minLon @4 :Float64;
  maxLat @5 :Float64;
  maxLon @6 :Float64;
  nodes @7 :List(Coordinates);
  lanes @8 :UInt8;
  advisorySpeed @9 :Float64;
  hazard @10 :Text;
  oneWay @11 :Bool;
  maxSpeedForward @12 :Float64;
  maxSpeedBackward @13 :Float64;
  id @14 :Int64;
  highwayClass @15 :HighwayClass;
  maxSpeedConditional @16 :Text;
  maxSpeedForwardConditional @17 :Text;
  maxSpeedBackwardConditional @18 :Text;
}

struct Coordinates {
  latitude @0 :Float64;
  longitude @1 :Float64;
}

struct Offline {
  minLat @0 :Float64;
  minLon @1 :Float64;
  maxLat @2 :Float64;
  maxLon @3 :Float64;
  ways @4 :List(Way);
  overlap @5 :Float64;
}
