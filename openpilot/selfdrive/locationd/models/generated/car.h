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
void car_err_fun(double *nom_x, double *delta_x, double *out_7378461606150437313);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_294189106821879139);
void car_H_mod_fun(double *state, double *out_4621094181659745510);
void car_f_fun(double *state, double dt, double *out_2614999472635489174);
void car_F_fun(double *state, double dt, double *out_7956648669823198257);
void car_h_25(double *state, double *unused, double *out_5695726182074513639);
void car_H_25(double *state, double *unused, double *out_5061492031990537509);
void car_h_24(double *state, double *unused, double *out_7087152536231624463);
void car_H_24(double *state, double *unused, double *out_7234141630996037075);
void car_h_30(double *state, double *unused, double *out_2067539074746158802);
void car_H_30(double *state, double *unused, double *out_1855198309501079246);
void car_h_26(double *state, double *unused, double *out_7069212342407004447);
void car_H_26(double *state, double *unused, double *out_1756966062229736908);
void car_h_27(double *state, double *unused, double *out_4033180971766345651);
void car_H_27(double *state, double *unused, double *out_319565002299345665);
void car_h_29(double *state, double *unused, double *out_2554646954709949512);
void car_H_29(double *state, double *unused, double *out_2032927729168896698);
void car_h_28(double *state, double *unused, double *out_8157738379984158711);
void car_H_28(double *state, double *unused, double *out_7115326746238427272);
void car_h_31(double *state, double *unused, double *out_5550206357853858668);
void car_H_31(double *state, double *unused, double *out_2015183218521279744);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}