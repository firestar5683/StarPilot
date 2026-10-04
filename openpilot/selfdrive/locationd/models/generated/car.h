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
void car_err_fun(double *nom_x, double *delta_x, double *out_3215893303801496185);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_147534577326453371);
void car_H_mod_fun(double *state, double *out_2952331916524662835);
void car_f_fun(double *state, double dt, double *out_1642637227976725443);
void car_F_fun(double *state, double dt, double *out_6364337859915327156);
void car_h_25(double *state, double *unused, double *out_8813185365055608935);
void car_H_25(double *state, double *unused, double *out_6475312566514154512);
void car_h_24(double *state, double *unused, double *out_3661129537260875279);
void car_H_24(double *state, double *unused, double *out_5317226049087211347);
void car_h_30(double *state, double *unused, double *out_5175735836801586585);
void car_H_30(double *state, double *unused, double *out_1947616236386546314);
void car_h_26(double *state, double *unused, double *out_2138949785357253900);
void car_H_26(double *state, double *unused, double *out_2733809247640098288);
void car_h_27(double *state, double *unused, double *out_8690048855752280246);
void car_H_27(double *state, double *unused, double *out_4171210307570489531);
void car_h_29(double *state, double *unused, double *out_50171379033738362);
void car_H_29(double *state, double *unused, double *out_2457847580700938498);
void car_h_28(double *state, double *unused, double *out_1254905421323579433);
void car_H_28(double *state, double *unused, double *out_4421477852266264749);
void car_h_31(double *state, double *unused, double *out_2666243543972910187);
void car_H_31(double *state, double *unused, double *out_6505958528391114940);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}