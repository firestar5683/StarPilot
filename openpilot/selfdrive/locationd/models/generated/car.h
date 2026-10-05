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
void car_err_fun(double *nom_x, double *delta_x, double *out_6746218398639626110);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_8789333614403809544);
void car_H_mod_fun(double *state, double *out_5287356164479477201);
void car_f_fun(double *state, double dt, double *out_4463126409710139018);
void car_F_fun(double *state, double dt, double *out_6080121800310696988);
void car_h_25(double *state, double *unused, double *out_6823959720500200939);
void car_H_25(double *state, double *unused, double *out_2633981868494382604);
void car_h_24(double *state, double *unused, double *out_6472024300223995676);
void car_H_24(double *state, double *unused, double *out_1793550084312337612);
void car_h_30(double *state, double *unused, double *out_5373328327871317772);
void car_H_30(double *state, double *unused, double *out_1893714461633225594);
void car_h_26(double *state, double *unused, double *out_8185880431141171155);
void car_H_26(double *state, double *unused, double *out_1107521450379673620);
void car_h_27(double *state, double *unused, double *out_178802983292864840);
void car_H_27(double *state, double *unused, double *out_4068477773433650505);
void car_h_29(double *state, double *unused, double *out_8071742478177388199);
void car_H_29(double *state, double *unused, double *out_1383483117318833410);
void car_h_28(double *state, double *unused, double *out_9160772155299705605);
void car_H_28(double *state, double *unused, double *out_6465882134388363984);
void car_h_31(double *state, double *unused, double *out_4419568396223364707);
void car_H_31(double *state, double *unused, double *out_1733729552613025096);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}