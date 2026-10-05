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
void car_err_fun(double *nom_x, double *delta_x, double *out_2204053027494663001);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_2041279983635365065);
void car_H_mod_fun(double *state, double *out_7031372799249316450);
void car_f_fun(double *state, double dt, double *out_1116747486686820994);
void car_F_fun(double *state, double dt, double *out_4929085835885003775);
void car_h_25(double *state, double *unused, double *out_3988698768583113995);
void car_H_25(double *state, double *unused, double *out_3508392149259824773);
void car_h_24(double *state, double *unused, double *out_4767470784617198679);
void car_H_24(double *state, double *unused, double *out_8254901476226333807);
void car_h_30(double *state, double *unused, double *out_7626148296837136345);
void car_H_30(double *state, double *unused, double *out_3408298192231791982);
void car_h_26(double *state, double *unused, double *out_2624475029176290700);
void car_H_26(double *state, double *unused, double *out_7249895468133880997);
void car_h_27(double *state, double *unused, double *out_572425478934043979);
void car_H_27(double *state, double *unused, double *out_1233534880431367071);
void car_h_29(double *state, double *unused, double *out_5818922509211569626);
void car_H_29(double *state, double *unused, double *out_3918529536546184166);
void car_h_28(double *state, double *unused, double *out_4389954518747249253);
void car_H_28(double *state, double *unused, double *out_5562226863507714536);
void car_h_31(double *state, double *unused, double *out_3713504706298608106);
void car_H_31(double *state, double *unused, double *out_3477746187382864345);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}