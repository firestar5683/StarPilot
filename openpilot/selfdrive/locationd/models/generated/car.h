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
void car_err_fun(double *nom_x, double *delta_x, double *out_1207054125356267807);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_3099046322898442676);
void car_H_mod_fun(double *state, double *out_8499267737788036021);
void car_f_fun(double *state, double dt, double *out_8282094013389197429);
void car_F_fun(double *state, double dt, double *out_2714751254066464584);
void car_h_25(double *state, double *unused, double *out_9062879424533513701);
void car_H_25(double *state, double *unused, double *out_6424495685932023918);
void car_h_24(double *state, double *unused, double *out_2252532558771607279);
void car_H_24(double *state, double *unused, double *out_2866570087129700782);
void car_h_30(double *state, double *unused, double *out_4624883595742397937);
void car_H_30(double *state, double *unused, double *out_3906162727424775291);
void car_h_26(double *state, double *unused, double *out_3556539275727349414);
void car_H_26(double *state, double *unused, double *out_8280745068903471474);
void car_h_27(double *state, double *unused, double *out_6779459328367340264);
void car_H_27(double *state, double *unused, double *out_1682568656240832074);
void car_h_29(double *state, double *unused, double *out_423756628618645706);
void car_H_29(double *state, double *unused, double *out_3395931383110383107);
void car_h_28(double *state, double *unused, double *out_7382775213043817781);
void car_H_28(double *state, double *unused, double *out_8478330400179913681);
void car_h_31(double *state, double *unused, double *out_8905692756182384556);
void car_H_31(double *state, double *unused, double *out_6393849724055063490);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}