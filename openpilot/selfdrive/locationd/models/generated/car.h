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
void car_err_fun(double *nom_x, double *delta_x, double *out_4839724972372252268);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_8829574174155035621);
void car_H_mod_fun(double *state, double *out_8175464074684333633);
void car_f_fun(double *state, double dt, double *out_6716121585907694027);
void car_F_fun(double *state, double dt, double *out_3872222255603432155);
void car_h_25(double *state, double *unused, double *out_2325222996689449646);
void car_H_25(double *state, double *unused, double *out_3271772249499668793);
void car_h_24(double *state, double *unused, double *out_6848076894841716204);
void car_H_24(double *state, double *unused, double *out_3303799557091849308);
void car_h_30(double *state, double *unused, double *out_8228581582135578611);
void car_H_30(double *state, double *unused, double *out_3644918091991947962);
void car_h_26(double *state, double *unused, double *out_7405610388304119622);
void car_H_26(double *state, double *unused, double *out_7013275568373725017);
void car_h_27(double *state, double *unused, double *out_2676450270971395999);
void car_H_27(double *state, double *unused, double *out_5575874508443333774);
void car_h_29(double *state, double *unused, double *out_1421853027307975865);
void car_H_29(double *state, double *unused, double *out_7289237235312884807);
void car_h_28(double *state, double *unused, double *out_6305518901035444766);
void car_H_28(double *state, double *unused, double *out_5325606963747558556);
void car_h_31(double *state, double *unused, double *out_2600417058973955535);
void car_H_31(double *state, double *unused, double *out_3241126287622708365);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}