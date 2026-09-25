@0xb526ba661d550a59;

# Exact StarPilotRadarState root/nested wire from frozen 678af783 custom.capnp.
struct StarPilotRadarState @0xb86e6369214c01c8 {
  leadLeft @0 :LeadData;
  leadRight @1 :LeadData;
  adjacentStopped @2 :AdjacentStopped;

  struct AdjacentStopped {
    status @0 :Bool;
    dRel @1 :Float32;
    yRel @2 :Float32;
    radarTrackId @3 :Int32 = -1;
  }

  struct LeadData {
    dRel @0 :Float32;
    yRel @1 :Float32;
    vRel @2 :Float32;
    aRel @3 :Float32;
    vLead @4 :Float32;
    dPath @6 :Float32;
    vLat @7 :Float32;
    vLeadK @8 :Float32;
    aLeadK @9 :Float32;
    fcw @10 :Bool;
    status @11 :Bool;
    aLeadTau @12 :Float32;
    modelProb @13 :Float32;
    radar @14 :Bool;
    radarTrackId @15 :Int32 = -1;

    aLeadDEPRECATED @5 :Float32;
  }
}
