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
void car_err_fun(double *nom_x, double *delta_x, double *out_5063363100648596688);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_1051973791362877167);
void car_H_mod_fun(double *state, double *out_5315869906856267240);
void car_f_fun(double *state, double dt, double *out_2679807483918754558);
void car_F_fun(double *state, double dt, double *out_8053926087528305413);
void car_h_25(double *state, double *unused, double *out_5716369086896639497);
void car_H_25(double *state, double *unused, double *out_3877318319055969997);
void car_h_24(double *state, double *unused, double *out_8949486097258288203);
void car_H_24(double *state, double *unused, double *out_6049967918061469563);
void car_h_30(double *state, double *unused, double *out_5873555755247768642);
void car_H_30(double *state, double *unused, double *out_3039372022435646758);
void car_h_26(double *state, double *unused, double *out_8147827403163551441);
void car_H_26(double *state, double *unused, double *out_7618821637930026221);
void car_h_27(double *state, double *unused, double *out_3868275412420834157);
void car_H_27(double *state, double *unused, double *out_864608710635221847);
void car_h_29(double *state, double *unused, double *out_2922753709018228498);
void car_H_29(double *state, double *unused, double *out_3549603366750038942);
void car_h_28(double *state, double *unused, double *out_2837524384607109846);
void car_H_28(double *state, double *unused, double *out_5931153033303859760);
void car_h_31(double *state, double *unused, double *out_7419317287452796635);
void car_H_31(double *state, double *unused, double *out_3846672357179009569);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}