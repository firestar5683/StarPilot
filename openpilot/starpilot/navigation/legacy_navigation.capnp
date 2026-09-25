@0xd78cc18827d186a2;
struct LegacyNavigation @0xded8e3c832d746a2 {
  sessionId @0 :Text;
  frameMonoTime @1 :UInt64;
  startedMonoTime @2 :UInt64;
  revision @3 :Text;
  enabled @4 :Bool;
  status @5 :Text;
  destinationName @6 :Text;
  instruction @7 :Instruction;
  route @8 :List(Coordinate);
  nextManeuver @9 :Instruction;
  locationMonoTime @10 :UInt64;
  controlValid @11 :Bool;

  struct Coordinate {
    latitude @0 :Float64;
    longitude @1 :Float64;
  }
  struct Instruction {
    text @0 :Text;
    maneuverType @1 :Text;
    maneuverModifier @2 :Text;
    distanceMeters @3 :Float32;
    remainingDistanceMeters @4 :Float32;
    remainingDurationSeconds @5 :Float32;
  }
}
