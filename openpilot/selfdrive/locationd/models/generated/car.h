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
void car_err_fun(double *nom_x, double *delta_x, double *out_7873944398687669040);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_6410436380803709543);
void car_H_mod_fun(double *state, double *out_1822083210648187229);
void car_f_fun(double *state, double dt, double *out_4879988995809842462);
void car_F_fun(double *state, double dt, double *out_7426947252524904028);
void car_h_25(double *state, double *unused, double *out_7648063682542478630);
void car_H_25(double *state, double *unused, double *out_7860503003002095790);
void car_h_24(double *state, double *unused, double *out_6113520950518082734);
void car_H_24(double *state, double *unused, double *out_4302577404199772654);
void car_h_30(double *state, double *unused, double *out_7923257744826984519);
void car_H_30(double *state, double *unused, double *out_5342170044494847163);
void car_h_26(double *state, double *unused, double *out_7919081008073869446);
void car_H_26(double *state, double *unused, double *out_4555977033241295189);
void car_h_27(double *state, double *unused, double *out_1249022165128629484);
void car_H_27(double *state, double *unused, double *out_7516933356295272074);
void car_h_29(double *state, double *unused, double *out_4886471693382651834);
void car_H_29(double *state, double *unused, double *out_4831938700180454979);
void car_h_28(double *state, double *unused, double *out_995235850125504438);
void car_H_28(double *state, double *unused, double *out_8532406356459566063);
void car_h_31(double *state, double *unused, double *out_6700377092887701122);
void car_H_31(double *state, double *unused, double *out_5182185135474646665);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}