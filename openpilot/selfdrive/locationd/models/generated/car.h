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
void car_err_fun(double *nom_x, double *delta_x, double *out_8602983957174335298);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_6809988399191804319);
void car_H_mod_fun(double *state, double *out_883537812237458096);
void car_f_fun(double *state, double dt, double *out_2449018896263561698);
void car_F_fun(double *state, double dt, double *out_9184524155541408120);
void car_h_25(double *state, double *unused, double *out_3274704919583746110);
void car_H_25(double *state, double *unused, double *out_6928939238479605978);
void car_h_24(double *state, double *unused, double *out_4314296844222658784);
void car_H_24(double *state, double *unused, double *out_6083942629695910579);
void car_h_30(double *state, double *unused, double *out_5365172557134795774);
void car_H_30(double *state, double *unused, double *out_4410606279972357351);
void car_h_26(double *state, double *unused, double *out_2552620453864942391);
void car_H_26(double *state, double *unused, double *out_7776301516355889414);
void car_h_27(double *state, double *unused, double *out_4256789012919044222);
void car_H_27(double *state, double *unused, double *out_2187012208788414134);
void car_h_29(double *state, double *unused, double *out_513112930423919314);
void car_H_29(double *state, double *unused, double *out_3900374935657965167);
void car_h_28(double *state, double *unused, double *out_4860104897595521739);
void car_H_28(double *state, double *unused, double *out_8982773952727495741);
void car_h_31(double *state, double *unused, double *out_2999510857299240221);
void car_H_31(double *state, double *unused, double *out_6898293276602645550);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}