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
void car_err_fun(double *nom_x, double *delta_x, double *out_2769656543589876252);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_6259280918951514600);
void car_H_mod_fun(double *state, double *out_6437777562673898302);
void car_f_fun(double *state, double dt, double *out_1051826260233084185);
void car_F_fun(double *state, double dt, double *out_4665134552691392129);
void car_h_25(double *state, double *unused, double *out_6902882259189952535);
void car_H_25(double *state, double *unused, double *out_2815778285123416077);
void car_h_24(double *state, double *unused, double *out_4770294784793454035);
void car_H_24(double *state, double *unused, double *out_5041486069102284639);
void car_h_30(double *state, double *unused, double *out_860382997630719906);
void car_H_30(double *state, double *unused, double *out_8714275447094518784);
void car_h_26(double *state, double *unused, double *out_5538658519783129240);
void car_H_26(double *state, double *unused, double *out_925725033750640147);
void car_h_27(double *state, double *unused, double *out_2079086912816888230);
void car_H_27(double *state, double *unused, double *out_7557705314814607921);
void car_h_29(double *state, double *unused, double *out_4141290270030125739);
void car_H_29(double *state, double *unused, double *out_8204044102780126600);
void car_h_28(double *state, double *unused, double *out_4683492233625585881);
void car_H_28(double *state, double *unused, double *out_5160300953859894442);
void car_h_31(double *state, double *unused, double *out_7504300416803316089);
void car_H_31(double *state, double *unused, double *out_2846424247000376505);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}