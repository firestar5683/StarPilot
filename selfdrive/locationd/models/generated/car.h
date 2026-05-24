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
void car_err_fun(double *nom_x, double *delta_x, double *out_8308214496735031777);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_8999766425853420329);
void car_H_mod_fun(double *state, double *out_8671923853756600219);
void car_f_fun(double *state, double dt, double *out_3762356930851513593);
void car_F_fun(double *state, double dt, double *out_110226856445903204);
void car_h_25(double *state, double *unused, double *out_5646094358831955306);
void car_H_25(double *state, double *unused, double *out_4871128394768286557);
void car_h_24(double *state, double *unused, double *out_7079061790558552168);
void car_H_24(double *state, double *unused, double *out_7374582999090103633);
void car_h_30(double *state, double *unused, double *out_2117170897988717135);
void car_H_30(double *state, double *unused, double *out_2352795436261037930);
void car_h_26(double *state, double *unused, double *out_7183588416707059858);
void car_H_26(double *state, double *unused, double *out_8612631713642342781);
void car_h_27(double *state, double *unused, double *out_3041689038023257655);
void car_H_27(double *state, double *unused, double *out_129201365077094713);
void car_h_29(double *state, double *unused, double *out_2884502369672128510);
void car_H_29(double *state, double *unused, double *out_1842564091946645746);
void car_h_28(double *state, double *unused, double *out_4902986578924970);
void car_H_28(double *state, double *unused, double *out_6924963109016176320);
void car_h_31(double *state, double *unused, double *out_8547812156113883153);
void car_H_31(double *state, double *unused, double *out_4840482432891326129);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}