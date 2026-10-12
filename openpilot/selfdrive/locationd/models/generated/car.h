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
void car_err_fun(double *nom_x, double *delta_x, double *out_8771745385019272911);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_3231363094273967832);
void car_H_mod_fun(double *state, double *out_5279329364050306118);
void car_f_fun(double *state, double dt, double *out_9065464123133416094);
void car_F_fun(double *state, double dt, double *out_4008021677178468012);
void car_h_25(double *state, double *unused, double *out_5404965656887369328);
void car_H_25(double *state, double *unused, double *out_5246076676685385693);
void car_h_24(double *state, double *unused, double *out_1243581068366124229);
void car_H_24(double *state, double *unused, double *out_1688151077883062557);
void car_h_30(double *state, double *unused, double *out_4545117735558442296);
void car_H_30(double *state, double *unused, double *out_8672971066896557725);
void car_h_26(double *state, double *unused, double *out_456555532102403349);
void car_H_26(double *state, double *unused, double *out_8987579995559441917);
void car_h_27(double *state, double *unused, double *out_338548138169026605);
void car_H_27(double *state, double *unused, double *out_6498207755096132814);
void car_h_29(double *state, double *unused, double *out_3601607882656779861);
void car_H_29(double *state, double *unused, double *out_9183202411210949909);
void car_h_28(double *state, double *unused, double *out_8457761326096970535);
void car_H_28(double *state, double *unused, double *out_4100803394141419335);
void car_h_31(double *state, double *unused, double *out_1509086364917783500);
void car_H_31(double *state, double *unused, double *out_8832955975916758223);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}