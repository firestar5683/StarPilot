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
void car_err_fun(double *nom_x, double *delta_x, double *out_6018065189512211380);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_1095263434101283480);
void car_H_mod_fun(double *state, double *out_2728844015902940614);
void car_f_fun(double *state, double dt, double *out_6525929466162239676);
void car_F_fun(double *state, double dt, double *out_2819353980597124361);
void car_h_25(double *state, double *unused, double *out_6189447245513617570);
void car_H_25(double *state, double *unused, double *out_3234178458103237326);
void car_h_24(double *state, double *unused, double *out_7649152206074051029);
void car_H_24(double *state, double *unused, double *out_7794173981929387397);
void car_h_30(double *state, double *unused, double *out_6334967069734272541);
void car_H_30(double *state, double *unused, double *out_3104839510959997256);
void car_h_26(double *state, double *unused, double *out_1333293802073426896);
void car_H_26(double *state, double *unused, double *out_507324860770818898);
void car_h_27(double *state, double *unused, double *out_7255623560535088401);
void car_H_27(double *state, double *unused, double *out_930076199159572345);
void car_h_29(double *state, double *unused, double *out_3730561748925574890);
void car_H_29(double *state, double *unused, double *out_3615070855274389440);
void car_h_28(double *state, double *unused, double *out_2029716344699763454);
void car_H_28(double *state, double *unused, double *out_1180343743855347563);
void car_h_31(double *state, double *unused, double *out_2551997717259595220);
void car_H_31(double *state, double *unused, double *out_3264824419980197754);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}