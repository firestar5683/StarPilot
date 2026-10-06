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
void car_err_fun(double *nom_x, double *delta_x, double *out_8477567103535527133);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_2667393315517795090);
void car_H_mod_fun(double *state, double *out_369087545671514402);
void car_f_fun(double *state, double dt, double *out_1005675647254068502);
void car_F_fun(double *state, double dt, double *out_5822543954406335876);
void car_h_25(double *state, double *unused, double *out_5908687060316855948);
void car_H_25(double *state, double *unused, double *out_8884468302125799977);
void car_h_24(double *state, double *unused, double *out_6456202694653818915);
void car_H_24(double *state, double *unused, double *out_6711818703120300411);
void car_h_30(double *state, double *unused, double *out_6370942973421561365);
void car_H_30(double *state, double *unused, double *out_2645585430092134884);
void car_h_26(double *state, double *unused, double *out_7314452826323223800);
void car_H_26(double *state, double *unused, double *out_5142964983251743753);
void car_h_27(double *state, double *unused, double *out_907013792656010303);
void car_H_27(double *state, double *unused, double *out_4820348741892559795);
void car_h_29(double *state, double *unused, double *out_8670279049476682744);
void car_H_29(double *state, double *unused, double *out_6533711468762110828);
void car_h_28(double *state, double *unused, double *out_4094659475004835342);
void car_H_28(double *state, double *unused, double *out_6830633587877910214);
void car_h_31(double *state, double *unused, double *out_8900607485138673318);
void car_H_31(double *state, double *unused, double *out_8915114264002760405);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}