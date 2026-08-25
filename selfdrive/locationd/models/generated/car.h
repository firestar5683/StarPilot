#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void car_update_25(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_24(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_30(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_26(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_27(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_29(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_28(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_31(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_err_fun(double *nom_x, double *delta_x, double *out_4436222918597397805);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_5455437002668972894);
void car_H_mod_fun(double *state, double *out_210375879520347438);
void car_f_fun(double *state, double dt, double *out_467846126367206141);
void car_F_fun(double *state, double dt, double *out_3146439140780538523);
void car_h_25(double *state, double *unused, double *out_3524127915259881655);
void car_H_25(double *state, double *unused, double *out_3733424518165712586);
void car_h_24(double *state, double *unused, double *out_5258226883159248845);
void car_H_24(double *state, double *unused, double *out_2842147288425805515);
void car_h_30(double *state, double *unused, double *out_2922709757646518101);
void car_H_30(double *state, double *unused, double *out_3183265823325904169);
void car_h_26(double *state, double *unused, double *out_2078963510014327544);
void car_H_26(double *state, double *unused, double *out_7474927837039768810);
void car_h_27(double *state, double *unused, double *out_9006985404715807625);
void car_H_27(double *state, double *unused, double *out_1008502511525479258);
void car_h_29(double *state, double *unused, double *out_1979199904744855666);
void car_H_29(double *state, double *unused, double *out_704860215344071775);
void car_h_28(double *state, double *unused, double *out_6835353348185046340);
void car_H_28(double *state, double *unused, double *out_5787259232413602349);
void car_h_31(double *state, double *unused, double *out_4974759307888764822);
void car_H_31(double *state, double *unused, double *out_3702778556288752158);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}