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
void car_err_fun(double *nom_x, double *delta_x, double *out_3018178744748463403);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_6060282748917342967);
void car_H_mod_fun(double *state, double *out_2864403739014660828);
void car_f_fun(double *state, double dt, double *out_5470700188972722037);
void car_F_fun(double *state, double dt, double *out_7150823736868333707);
void car_h_25(double *state, double *unused, double *out_264395063841365559);
void car_H_25(double *state, double *unused, double *out_8902644214858585877);
void car_h_24(double *state, double *unused, double *out_5091830536703747687);
void car_H_24(double *state, double *unused, double *out_517398855874799444);
void car_h_30(double *state, double *unused, double *out_1715026456470248726);
void car_H_30(double *state, double *unused, double *out_1985953873366969122);
void car_h_26(double *state, double *unused, double *out_2318342341146726243);
void car_H_26(double *state, double *unused, double *out_5598118245097785276);
void car_h_27(double *state, double *unused, double *out_717689029493932553);
void car_H_27(double *state, double *unused, double *out_4160717185167394033);
void car_h_29(double *state, double *unused, double *out_992883091778438442);
void car_H_29(double *state, double *unused, double *out_5874079912036945066);
void car_h_28(double *state, double *unused, double *out_2197617134068279513);
void car_H_28(double *state, double *unused, double *out_7490265144603075976);
void car_h_31(double *state, double *unused, double *out_8145667714595414744);
void car_H_31(double *state, double *unused, double *out_1825968964346768624);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}