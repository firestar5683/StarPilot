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
void car_err_fun(double *nom_x, double *delta_x, double *out_9105893539066631470);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_2201885575610208115);
void car_H_mod_fun(double *state, double *out_8823093076762317206);
void car_f_fun(double *state, double dt, double *out_8757684582265239992);
void car_F_fun(double *state, double dt, double *out_2903520854157127208);
void car_h_25(double *state, double *unused, double *out_6353487808218647336);
void car_H_25(double *state, double *unused, double *out_430462771034997173);
void car_h_24(double *state, double *unused, double *out_276973526775545327);
void car_H_24(double *state, double *unused, double *out_1742186827970502393);
void car_h_30(double *state, double *unused, double *out_2255184509939275472);
void car_H_30(double *state, double *unused, double *out_2948795729542245800);
void car_h_26(double *state, double *unused, double *out_1273100416603977360);
void car_H_26(double *state, double *unused, double *out_3734988740795797774);
void car_h_27(double *state, double *unused, double *out_2052169011425579317);
void car_H_27(double *state, double *unused, double *out_774032417741820889);
void car_h_29(double *state, double *unused, double *out_7256857777600121117);
void car_H_29(double *state, double *unused, double *out_3459027073856637984);
void car_h_28(double *state, double *unused, double *out_2373191903872652216);
void car_H_28(double *state, double *unused, double *out_1623371943212892590);
void car_h_31(double *state, double *unused, double *out_6078293745934141447);
void car_H_31(double *state, double *unused, double *out_3108780638562446298);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}