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
void car_err_fun(double *nom_x, double *delta_x, double *out_7265162447446229961);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_2534123790686773518);
void car_H_mod_fun(double *state, double *out_1384469192892797747);
void car_f_fun(double *state, double dt, double *out_9101897029961662559);
void car_F_fun(double *state, double dt, double *out_680747621702192134);
void car_h_25(double *state, double *unused, double *out_952224570279587019);
void car_H_25(double *state, double *unused, double *out_1889803635093094459);
void car_h_24(double *state, double *unused, double *out_7823167244385071821);
void car_H_24(double *state, double *unused, double *out_5891515713723603092);
void car_h_30(double *state, double *unused, double *out_8854642026711422713);
void car_H_30(double *state, double *unused, double *out_8806493976584711214);
void car_h_26(double *state, double *unused, double *out_8251326142034945196);
void car_H_26(double *state, double *unused, double *out_1851699683780961765);
void car_h_27(double *state, double *unused, double *out_3989010621723919704);
void car_H_27(double *state, double *unused, double *out_6631730664784286303);
void car_h_29(double *state, double *unused, double *out_7686898225635280976);
void car_H_29(double *state, double *unused, double *out_9130018752810448218);
void car_h_28(double *state, double *unused, double *out_1236896594111405243);
void car_H_28(double *state, double *unused, double *out_4234326303829572824);
void car_h_31(double *state, double *unused, double *out_1227418632564092908);
void car_H_31(double *state, double *unused, double *out_1920449596970054887);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}