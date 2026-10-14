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
void car_err_fun(double *nom_x, double *delta_x, double *out_8401062644651369313);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_1597386426371446775);
void car_H_mod_fun(double *state, double *out_6673047517466386074);
void car_f_fun(double *state, double dt, double *out_9084958235864333770);
void car_F_fun(double *state, double dt, double *out_7170567397506903651);
void car_h_25(double *state, double *unused, double *out_2817491058203070073);
void car_H_25(double *state, double *unused, double *out_2580508330330928305);
void car_h_24(double *state, double *unused, double *out_1256144265869621667);
void car_H_24(double *state, double *unused, double *out_2239813174325059958);
void car_h_30(double *state, double *unused, double *out_3770336868273225090);
void car_H_30(double *state, double *unused, double *out_2451169383187688235);
void car_h_26(double *state, double *unused, double *out_5250206544167251352);
void car_H_26(double *state, double *unused, double *out_1160994988543127919);
void car_h_27(double *state, double *unused, double *out_4831854115108264269);
void car_H_27(double *state, double *unused, double *out_276406071387263324);
void car_h_29(double *state, double *unused, double *out_733550816828892405);
void car_H_29(double *state, double *unused, double *out_2961400727502080419);
void car_h_28(double *state, double *unused, double *out_4150115056898576496);
void car_H_28(double *state, double *unused, double *out_4925030999067406670);
void car_h_31(double *state, double *unused, double *out_6454940586457092423);
void car_H_31(double *state, double *unused, double *out_2611154292207888733);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}